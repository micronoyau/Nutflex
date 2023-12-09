"""
Watermark videos with unique ID using spread spectrum watermarking
@authors : micronoyau and devilsharu
"""

import sys
from typing import Callable

# Video & image processing
import cv2
import av
from PIL import Image

# Math
import numpy as np

# Cute bar
from alive_progress import alive_bar

# Bitstream
from bitstring import ConstBitStream, BitArray, Bits, ReadError

# CLI usage
import argparse

CHANNEL = 0 # For test purposes


def compute_G(key: int, n_dct: int) -> np.array:
    """
    Derive a matrix from a secret key [key]
    Since only the DCT coefficients are watermarked, we need to specify [n_dct]
    to specify the size of the encoded vector (n = n_dct*n_dct).
    """
    # Seed with key
    np.random.seed(key)
    return 2*np.random.randint(2, size=(n_dct*n_dct))-1


def get_middle_coefs_slice(array_dct: np.array, n_dct: int):
    """
    Returns a slice of the middle DCT coefficients
    """
    # Consider only middle coefficients
    arr_sz = array_dct.shape
    midx, midy = arr_sz[0]//2, arr_sz[1]//2
    return array_dct[midx-(n_dct//2):midx+(n_dct - n_dct//2), midy-(n_dct//2):midy+(n_dct - n_dct//2)]


def open_existing_movie(movie_filename: str):
    """
    Returns video and audio packets
    """
    # Opens the stream and packets for video
    container = av.open(movie_filename)
    video_stream = container.streams.video[0]
    video_packets = list(container.demux(video_stream))

    # Opens the stream and packets for audio
    container = av.open(movie_filename)
    audio_stream = container.streams.audio[0]
    audio_packets = list(container.demux(audio_stream))

    return video_packets, audio_packets, video_stream, audio_stream


def create_movie_from(video_stream, audio_stream, output_filename: str):
    """
    Create a video file from video and audio streams
    """
    # Creates a container for the output movie
    output_container = av.open(output_filename, mode="w")

    # Specify the video options for the created video
    codec_name = video_stream.codec_context.name
    fps = video_stream.average_rate
    output_video_stream = output_container.add_stream('libx264', str(fps))
    output_video_stream.options = {'x264-params': 'keyint=24:min-keyint=24:scenecut=0' }
    output_video_stream.width = video_stream.codec_context.width
    width = video_stream.codec_context.width
    output_video_stream.height = video_stream.codec_context.height
    height = video_stream.codec_context.height
    output_video_stream.pix_fmt = video_stream.codec_context.pix_fmt

    # Specify the audio options for the created video
    output_audio_stream = output_container.add_stream(template=audio_stream)

    return output_container, output_video_stream, output_audio_stream


class VideoIterator:
    """
    An iterator to simplify iteration through video and audio packets 
    """

    def __init__(self, input_video_packets, input_audio_packets, bar=None):
        self.input_video_packets = input_video_packets
        self.input_audio_packets = input_audio_packets
        self.bar = bar


    def __iter__(self):
        self.video_index = 0
        self.audio_index = 0
        return self


    def __next__(self):
        if self.audio_index < len(self.input_audio_packets) or self.video_index < len(self.input_video_packets):
            audio_packet = None
            if self.audio_index < len(self.input_audio_packets):

                if self.input_audio_packets[self.audio_index].dts is None:
                    self.audio_index += 1
                    return self.__next__()

                audio_packet = self.input_audio_packets[self.audio_index]

            video_packet = None
            if self.video_index < len(self.input_video_packets):

                if self.input_video_packets[self.video_index].dts is None:
                    self.video_index += 1
                    if self.bar:
                        self.bar()
                    return self.__next__()

                video_packet = self.input_video_packets[self.video_index]

            if (video_packet is None) or (audio_packet is not None and audio_packet.dts < video_packet.dts):
                self.audio_index += 1
            else:
                self.video_index += 1
                if self.bar:
                    self.bar()

            return (video_packet, audio_packet)

        else:
            raise StopIteration


def encode_watermark(symbol: bool, key: int, n_dct: int, alpha: float, movie_filename: str, watermarked_filename: str) -> None:
    """
    Encode symbol [symbol] in [watermarked_filename] using private key [key]
    and spread spectrum parameters [n_dct] (size of modified DCT square) and [alpha] (strength)
    """
    G = compute_G(key, n_dct)
    input_video_packets, input_audio_packets, input_video_stream, input_audio_stream = open_existing_movie(movie_filename)
    watermarked_container, watermarked_video_stream, watermarked_audio_stream = create_movie_from(input_video_stream, input_audio_stream, watermarked_filename)

    with alive_bar(len(input_video_packets)) as bar:
        video_iterator = VideoIterator(input_video_packets, input_audio_packets, bar=bar)

        for video_packet, audio_packet in iter(video_iterator):
            if (video_packet is None) or ((audio_packet is not None) and (audio_packet.dts < video_packet.dts)):
                audio_packet.stream = watermarked_audio_stream
                watermarked_container.mux(audio_packet)
                continue

            for frame in video_packet.decode():
                image = frame.to_image()
                array = np.array(image)

                array_dct = cv2.dct(array[:,:,CHANNEL]/255)
                # Middle coefficients
                middle_slice = get_middle_coefs_slice(array_dct, n_dct)
                # Watermark
                w = np.reshape(alpha * (G if symbol else -G), (n_dct,n_dct))
                # y = x+w
                middle_slice += w
                # Keep DCT coefficients between 0 and 1
                middle_slice = np.minimum(np.maximum(middle_slice, 0), 1)
                # Convert back to image from frequency domain
                array[:,:,CHANNEL] = cv2.idct(array_dct*255)

                image = Image.fromarray(array)
                out_frame = av.VideoFrame.from_image(image)
                out_packet = watermarked_video_stream.encode(out_frame)
                watermarked_container.mux(out_packet)


    try:
        for packet in watermarked_video_stream.encode():
            watermarked_container.mux(packet)

    except EOFError:
        print("ERROR when writing to video file")

    watermarked_container.close()


def encode_AB(msg: bytes, input_A_filename: str, input_B_filename: str, out_filename: str, freq: float) -> None:
    """
    Encode message [msg] in [out_filename] using an A/B encoding procedure
    with input files [input_A_filename] and [input_B_filename] at frequency [freq]
    """
    bs = ConstBitStream(msg)[::-1]

    input_A_video_packets, input_A_audio_packets, input_A_video_stream, input_A_audio_stream = open_existing_movie(input_A_filename)
    input_B_video_packets, input_B_audio_packets, input_B_video_stream, input_B_audio_stream = open_existing_movie(input_B_filename)
    out_container, out_video_stream, out_audio_stream = create_movie_from(input_A_video_stream, input_A_audio_stream, out_filename)

    assert len(input_A_video_packets) == len(input_B_video_packets)
    fps = input_A_video_stream.average_rate
    assert fps == input_B_video_stream.average_rate

    skip_frames = int(fps / freq)
    frames = 0
    frame_index = 0

    with alive_bar(len(input_A_video_packets)) as bar:
        video_iterator_A = VideoIterator(input_A_video_packets, input_A_audio_packets, bar=bar)
        video_iterator_B = VideoIterator(input_B_video_packets, input_B_audio_packets)

        for (video_packet_A, audio_packet_A), (video_packet_B, audio_packet_B) in zip(iter(video_iterator_A), iter(video_iterator_B)):
            if (video_packet_A is None) or ((audio_packet_A is not None) and (audio_packet_A.dts < video_packet_A.dts)):
                audio_packet_A.stream = out_audio_stream
                out_container.mux(audio_packet_A)
                continue

            for (f1, f2) in zip(video_packet_A.decode(), video_packet_B.decode()):
                if frames == 0:
                    try:
                        frame_index = bs.read(1).bool
                    except ReadError: # By default, add
                        frame_index = 0

                f = (f1,f2)[frame_index]

                out_packet = out_video_stream.encode(f)
                out_container.mux(out_packet)

                frames = (frames+1) % skip_frames

    try:
        for packet in out_video_stream.encode():
            out_container.mux(packet)

    except EOFError:
        print("ERROR when writing to video file")

    out_container.close()


def decode_AB(key: int, n_dct: int, movie_filename: str, freq: float) -> BitArray:
    """
    Extract message from video [movie_filename]at frequence [freq]
    with secret key [key] and DCT square size [n_dct]
    """
    decoded = BitArray()

    G = compute_G(key, n_dct)
    video_packets, audio_packets, video_stream, audio_stream = open_existing_movie(movie_filename)

    fps = video_stream.average_rate

    skip_frames = int(fps / freq)
    frames = 0
    c = 0 # sum of correlations

    with alive_bar(len(video_packets)) as bar:
        video_iterator = VideoIterator(video_packets, audio_packets, bar=bar)

        for video_packet, audio_packet in iter(video_iterator):
            if (video_packet is None) or ((audio_packet is not None) and (audio_packet.dts < video_packet.dts)):
                continue

            for frame in video_packet.decode():
                frames = (frames+1) % skip_frames

                if frames == 0:
                    decoded.append(Bits('0b1' if c<=0 else '0b0'))
                    c = 0
                    continue

                image = frame.to_image()
                array = np.array(image)

                array_dct = cv2.dct(array[:,:,CHANNEL]/255)
                middle_slice = get_middle_coefs_slice(array_dct, n_dct)
                c += np.dot(G, middle_slice.flatten())

    return decoded[::-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        prog='Nutflex',
                        description='Watermark ID in video')

    parser.add_argument('action', choices=['w', 'e', 'd'], help='w (watermark)\ne (encode using A/B scheme)\nd (decode)')

    parser.add_argument('-k', '--key', type=int, nargs=1)
    parser.add_argument('-n', '--n-dct', type=int, nargs=1)
    parser.add_argument('-i', '--input', type=str, nargs='+', help='Input filename')
    parser.add_argument('-o', '--output', type=str, nargs=1, help='Output filename')
    parser.add_argument('-t', '--type', choices=[0,1], type=int, nargs=1, help='Type of watermarking')
    parser.add_argument('-a', '--alpha', type=float, nargs=1, help='Type of watermarking')
    parser.add_argument('-m', '--message', type=int, nargs=1, help='Message (ID) to hide')
    parser.add_argument('-f', '--frequency', type=float, nargs=1, help='Frequency of encoding')

    args = parser.parse_args()

    if args.action == 'w':
        if None in (args.type, args.key, args.n_dct, args.alpha, args.input, args.input, args.output) or len(args.input) != 1:
            parser.error('watermarking requires type, key, n-dct, alpha, input and output')

        encode_watermark(args.type[0], args.key[0], args.n_dct[0], args.alpha[0], args.input[0], args.output[0])

    if args.action == 'e':
        if None in (args.message, args.input, args.output, args.frequency) or len(args.input) != 2:
            parser.error('encoding requires message, 2 input video files A and B, output and an encoding frequency')

        encode_AB(args.message[0].to_bytes(), args.input[0], args.input[1], args.output[0], args.frequency[0])

    if args.action == 'd':
        if None in (args.key, args.n_dct, args.input, args.frequency) or len(args.input) != 1:
            parser.error('decoding requires key, n-dct, input and frequency')

        print(decode_AB(args.key[0], args.n_dct[0], args.input[0], args.frequency[0]).b)

