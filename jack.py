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

# Video & image processing
import cv2
import av
from PIL import Image

# Math
import numpy as np

# Cute bar
from alive_progress import alive_bar


def embed(symbol: bool, key: int, n_dct, movie_filename, watermarked_filename):
    """
    Embeds symbol [symbol] in movie [movie_filename] to produce [watermarked_filename]
    [key] is the secret key used to generate G
    The matrix of the smallest dct coefs is of size [n_dct]*[n_dct]
    [symbol] takes value 0 (False) or 1 (True)
    """
    # Seed with key
    np.random.seed(key)

    # Opens the stream and packets for video
    container_input = av.open(movie_filename)
    input_video_stream = container_input.streams.video[0]
    input_video_packets = list(container_input.demux(input_video_stream))

    # Opens the stream and packets for audio
    container_input = av.open(movie_filename)
    input_audio_stream = container_input.streams.audio[0]
    input_audio_packets = list(container_input.demux(input_audio_stream))

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

    # Creates a video with audio
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
                audio_packet.stream = watermarked_audio_stream
                watermarked_container.mux(audio_packet)
                audio_index += 1
                continue

            G = 2*np.random.randint(2, size=(n_dct*n_dct))-1
            CHANNEL = 0 # For test purposes

            for frame in video_packet.decode():
                image = frame.to_image()
                array = np.array(image)

                # ==============================================================================
                # YOUR CODE GOES HERE
                # ==============================================================================
                # Array is a numpy array containing the frame information, it can be modified.

                array_dct = cv2.dct(array[:,:,CHANNEL]/255)

                # Take dct with smaller coefficient

                smaller_coefs = array_dct[-n_dct-1:-1,-n_dct-1:-1]
                
                arr_sz = array_dct.shape
                midx, midy = arr_sz[0]//2, arr_sz[1]//2
                
                smaller_coefs = array_dct[midx-(n_dct//2):midx+(n_dct - n_dct//2), midy-(n_dct//2):midy+(n_dct - n_dct//2)]

                w = np.reshape(G * smaller_coefs.flatten(), (n_dct,n_dct))

                # Add to obtain y
                array_dct[midx-(n_dct//2):midx+(n_dct - n_dct//2), midy-(n_dct//2):midy+(n_dct - n_dct//2)] += w

                # Bounds : check
                array_dct[midx-(n_dct//2):midx+(n_dct - n_dct//2), midy-(n_dct//2):midy+(n_dct - n_dct//2)] = np.minimum(np.maximum(array_dct[midx-(n_dct//2):midx+(n_dct - n_dct//2), midy-(n_dct//2):midy+(n_dct - n_dct//2)], 0), 1)

                array[:,:,CHANNEL] = cv2.idct(array_dct*255)

                # ==============================================================================

                image = Image.fromarray(array)
                out_frame = av.VideoFrame.from_image(image)
                out_packet = watermarked_video_stream.encode(out_frame)
                watermarked_container.mux(out_packet)

            video_index += 1
            bar()

    try:
        for packet in watermarked_video_stream.encode():
            watermarked_container.mux(packet)
    except EOFError:
        print("ERROR")

    watermarked_container.close()


if __name__ == '__main__':
    if len(sys.argv) == 3:
        embed(False, 0, 4, sys.argv[1], sys.argv[2])
    else:
        print("Usage {} input_movie watermarked_movie".format(sys.argv[0]))
