from main import *
from pytube import YouTube
import os
import time
from moviepy.editor import VideoFileClip


def downloadYouTube(videourl, path,tag):

    yt = YouTube(videourl)
    #yt = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').asc().first()
    yt = yt.streams.filter(progressive=True, file_extension='mp4',res="360p").first()
    if not os.path.exists(path):
        os.makedirs(path)
    path = yt.download(path)
    os.rename(path,"movies/"+tag+".mp4")


def compress_mp4(input_file, output_file, compression_factor=0.5):
    try:
        # Load the video clip
        clip = VideoFileClip(input_file)

        video = clip
        mp3 = video.audio
        if mp3 is not None:
            mp3.write_audiofile("vid_audio.mp3")
        mp3_size =  os.path.getsize("vid_audio.mp3")
        vid_size = os.path.getsize(input_file)
        duration = video.duration


        bitrate = int((((vid_size - mp3_size)/duration)/1024*8))
        # Reduce the bitrate to achieve compression
        new_bitrate = f'{bitrate * compression_factor}k'
        print (new_bitrate)
        # Write the compressed video to the output file
        clip.write_videofile(output_file, codec='libx264', audio_codec='aac', ffmpeg_params=['-b', new_bitrate])

        print(f'Successfully compressed {input_file} to {output_file}')
    except Exception as e:
        print(f'Error during compression: {e}')

#Open the file containing the links and tags of all the trailers we need
listOfFilm = open("movies/list.txt","r")

#List already downloaded trailers
alreadyDownloaded = os.listdir("movies/")

for links in listOfFilm:
    link = links.strip().split(" ")[0]
    tag = links.strip().split(" ")[1]
    if tag+".mp4" not in alreadyDownloaded:
        downloadYouTube(link, 'movies/',tag)

#Update list of downloaded movies
alreadyDownloaded = os.listdir("movies/")
print(alreadyDownloaded)


for movie in alreadyDownloaded:
    if movie != 'list.txt':
        dataOutput = open('results/'+movie+"_data.txt","a")
        currMovieFile = "movies/"+movie
        for alpha in [0.005,0.01,0.02,0.05,0.1,0.2,0.4,0.8,1.5,2,3,4,5]:
            for n_dct in [1,2,4,8,10,14,16,20,25,30]:
                print(f"alpha : {alpha} | n_dct : {n_dct}\n")
                beforeTime = time.time()
                encode_watermark(0, 42, n_dct, alpha, currMovieFile, "out/current_0.mp4")
                encode_watermark(1, 42, n_dct, alpha, currMovieFile, "out/current_1.mp4")
                msg = 314159
                encode_AB(msg.to_bytes((msg//256)+1), 'out/current_0.mp4', 'out/current_1.mp4','out/current_uncompressed.mp4', 0.5)
                middleTime = time.time()
                encoding_time = middleTime - beforeTime
                res,confidence = decode_AB(42, n_dct, "out/current_uncompressed.mp4", 0.5)
                decoding_time = time.time() - middleTime

                dataOutput.write(f'{movie} {alpha} {n_dct} {encoding_time} {decoding_time} {res.u} {confidence} 100\n')

                for compression in [75,50,25,10]:
                    compress_mp4('out/current_uncompressed.mp4','out/current_compressed_'+str(compression)+".mp4",compression/100)
                    beforeDecodeTime = time.time()
                    res,confidence = decode_AB(42, n_dct, "out/current_compressed_"+str(compression)+".mp4", 0.5)
                    decodingCompressedTime = time.time() - beforeDecodeTime

                    dataOutput.write(f'{movie} {alpha} {n_dct} {encoding_time} {decodingCompressedTime} {res.u} {confidence} {compression}\n')