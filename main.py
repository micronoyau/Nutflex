'''
A quick PyAv example that adds a colored square to the middle of a video.

For the purposes of the course, you want to modify and copy the embed
functions.

Starting at line 100 you have access to a numpy array containing the rgb
values of the frame.

The author disclaims copyright to this source code.  In place of a legal
notice, here is a blessing:

  May you do good and not evil.
  May you find forgiveness for yourself and forgive others.
  May you share freely, never taking more than you give.
'''

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


def iterate_video_frames(movie_filename: str, watermarked_filename: str, callback: Callable) -> None:
    """
    Iterates through the frames of the input video [movie_filename].
    If [watermarked_filename] is non-null, also creates and writes to video.
    The core functionnality is provided by [callback], a function that takes
    a numpy array representing a frame
    """
    # List containing all the return values from callbacks
    ret = []

    # Opens the stream and packets for video
    container_input = av.open(movie_filename)
    input_video_stream = container_input.streams.video[0]
    input_video_packets = list(container_input.demux(input_video_stream))

    # Opens the stream and packets for audio
    container_input = av.open(movie_filename)
    input_audio_stream = container_input.streams.audio[0]
    input_audio_packets = list(container_input.demux(input_audio_stream))

    if watermarked_filename:
        # Creates a container for the output movie
        watermarked_container = av.open(watermarked_filename, mode="w")

        # Specify the video options for the created video
        codec_name = input_video_stream.codec_context.name
        fps = input_video_stream.average_rate
        watermarked_video_stream = watermarked_container.add_stream('libx264', str(fps))
        watermarked_video_stream.options = {'x264-params': 'keyint=24:min-keyint=24:scenecut=0' }
        watermarked_video_stream.width = input_video_stream.codec_context.width
        width = input_video_stream.codec_context.width
        watermarked_video_stream.height = input_video_stream.codec_context.height
        height = input_video_stream.codec_context.height
        watermarked_video_stream.pix_fmt = input_video_stream.codec_context.pix_fmt

        # Specify the audio options for the created video
        watermarked_audio_stream = watermarked_container.add_stream(template=input_audio_stream)

    video_index = 0
    audio_index = 0

    with alive_bar(len(input_video_packets)) as bar:
        while((audio_index < len(input_audio_packets)) or ((video_index < len(input_video_packets)))):
            audio_packet = None

            if audio_index < len(input_audio_packets):
                if input_audio_packets[audio_index].dts is None:
                    audio_index += 1
                    continue
                audio_packet = input_audio_packets[audio_index]

            video_packet = None

            if video_index < len(input_video_packets):
                if input_video_packets[video_index].dts is None:
                    video_index += 1
                    bar()
                    continue
                video_packet = input_video_packets[video_index]

            if (video_packet is None) or ((audio_packet is not None) and (audio_packet.dts < video_packet.dts)):
                if watermarked_filename:
                    audio_packet.stream = watermarked_audio_stream
                    watermarked_container.mux(audio_packet)

                audio_index += 1
                continue

            for frame in video_packet.decode():
                image = frame.to_image()
                array = np.array(image)

                ret.append(callback(array))

                if watermarked_filename:
                    image = Image.fromarray(array)
                    out_frame = av.VideoFrame.from_image(image)
                    out_packet = watermarked_video_stream.encode(out_frame)
                    watermarked_container.mux(out_packet)

            video_index += 1
            bar()

    if watermarked_filename:
        try:
            for packet in watermarked_video_stream.encode():
                watermarked_container.mux(packet)
        except EOFError:
            print("ERROR when writing to video file")

        watermarked_container.close()

    return ret


def encode_core(symbol: bool, G: np.array, n_dct: int, alpha: float, array: np.array) -> None:
    """
    Core of encoding function
    """
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


def encode(symbol: bool, key: int, n_dct: int, alpha: float, movie_filename: str, watermarked_filename: str) -> None:
    """
    Embeds symbol [symbol] in movie [movie_filename] to produce [watermarked_filename]
    [key] is the secret key used to generate G
    The matrix of the middle dct coefs is of size [n_dct]*[n_dct]
    [symbol] takes value 0 (False) or 1 (True)
    [alpha] is the power of the watermark
    """
    G = compute_G(key, n_dct)
    iterate_video_frames(movie_filename, watermarked_filename, lambda array: encode_core(symbol, G, n_dct, alpha, array))


def decode_core(G: np.array, n_dct: int, array: np.array) -> bool:
    """
    Core of decoding function
    """
    array_dct = cv2.dct(array[:,:,CHANNEL]/255)
    middle_slice = get_middle_coefs_slice(array_dct, n_dct)
    c = np.dot(G, middle_slice.flatten())
    return c <= 0 # Reversed compared to the lecture


## TODO : change this function to extract A/B ##
def decode(key: int, n_dct: int, movie_filename: str) -> bool:
    """
    Decode 1 bit from frame [frame]
    c = G^T * r with r the attacked-watermarked vector
    """
    G = compute_G(key, n_dct)
    decoded = iterate_video_frames(movie_filename, None, lambda array: decode_core(G, n_dct, array))
    return False


if __name__ == '__main__':
    if len(sys.argv) == 8 and sys.argv[1] == 'encode':
        encode(sys.argv[2] == '1', int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6], sys.argv[7])

    elif len(sys.argv) == 5 and sys.argv[1] == 'decode':
        decode(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])

    else:
        print("Usage {} encode [symbol] [key] [n_dct] [alpha] [input movie] [watermarked movie]".format(sys.argv[0]))
        print("      {} decode [key] [n_dct] [watermarked movie]".format(sys.argv[0]))
