"""
It took some time
"""

import os
import subprocess
import shutil
import re
import pathlib

def get_files(folder: str):
    """
    This Function takes path to a directory and returns all the files(no directory) inside as a list. 
    Caution: IT is not necessary that files are in same order as shown in file explorer
    """
    _, _, filenames = next(os.walk(folder))
    return [n for n in filenames if n[0] != '.']

def setup_directories():
    """
    This Function will check for data and audio directory existence and will create videos and 
    videos/output folders as well and during process return true or false accordingly
    """
    if not os.path.isdir("audio"):
        return False
    if not os.path.isdir("data"):
        return False

    try:
        if not os.path.isdir("videos"):
            os.mkdir("videos")
        if not os.path.isdir("videos/output"):
            os.mkdir("videos/output")
        return True
    except OSError as error:  
        print(error)
        return False

def video_size(file_name: str, path: str=""):
    """
    This function uses ffprobe from ffmpeg package to get duration of 
    video or audio file being passed to it and returns duration as float
    """
    try:
        args = ["ffprobe", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", "\"{0}\"".format(path + file_name)]
        output = subprocess.check_output("ffprobe -show_entries format=duration -v quiet -of csv=\"p=0\" \"{0}\"".format("./" + path + file_name), shell=True)
        video_length = float(output.decode('utf-8'))
        return video_length
        
    except subprocess.CalledProcessError as e:
        print(e.output)
        print(e)
        return 0.0

def crop_video(file_name: str, path: str="", out_path: str=""):
    """
    This function takes name and path(both source file and destination) of file as string input
    and crop the video with aspect ration of 1:1 and then scale it to 1080x1080 
    and return its destination path with original file name
    This conerts the mp4 to MTS format for faster performance wich costs us some amount
    of video quality
    """
    os.system('''ffmpeg -i \"{0}\" -vf "crop='min(iw,1*ih)':'min(iw/1,ih)',scale=1080:1080" \"{1}\"'''.format(
        path + file_name, out_path + (file_name.split('.'))[0] + '.MTS'))
    return (file_name.split('.'))[0] + '.MTS'

def intake_files(index: int, files: list, total_files: int):
    """
     This function calculates how many files are required to make minimum of 
     3min video from the point/index where last batch ended
     This Function takes list of all file names, starting index from 
     where to start reading the list and total length of list
     and returns 2 parameters (list of )
    """

    video_group = []
    video_length = 0
    while (index < total_files and video_length < 180):
        video_length = video_length + video_size(files[index], "data/")
        video_group.append(files[index])
        index = index + 1

    return video_group, video_length

def combine_files(files: list, path: str="", out_path: str="", file_name: str=""):
    """
    This function will take a list of filenames with path and then put their names
    in a text file, which will then be used as a parameter in the below ffmpeg command
    which concatenates the files with their names inside a given text file
    It will also receive an output filename which will be the name of final file
    """
    file = open(path + "files.txt","w")
    for i in range(0, len(files)):
        file.write("file " + "\'" + files[i]+ "\'" + "\n")
    file.close()
    
    os.system("ffmpeg -f concat -i {0}files.txt -c:a copy -c:v libx264 -preset veryfast -crf 18 -f mp4 {1}".format("videos/", out_path + file_name))
    return file_name
    
def replce_audio(file_name: str, path: str="", audio_file: str="", path_to_audio: str="audio/"):
    """
    This function replaces the audio of a given video file with the provided
    audio file, and returns the final file with the original file name having a prefix 
    Final attached to it
    Note: The command is set in such a way that it will clip the audio if it exceed the 
    video's length
    """
    os.system("ffmpeg -i \"{0}\" -i \"{1}\" -filter_complex \" [1:0] apad \" -shortest \"{2}\"".format
              (path + file_name, path_to_audio + audio_file, path + "Final" + file_name))

def delete_temp(files: list, path: str):
    """
    This function will delete the files with names passes in the list and path to their folder
    """
    try:
        for item in files:
            os.remove(path + item)
    except Exception as e:
        print(e)

def combine_audio(file: str, path: str, length: int):
    """
    This function takes an audio file and combine it with itself(repeat) until it matches the length parameter
    It works only for mp3 and wav formats
    It will store the final file with name output.mp3 which will be deleted inside the main function once used
    """
    extension = file.split(".")
    wav_file = file
    
    # if audio file is wav format then first reencode it to mp3 and then do the self concatenation
    # otherwise it will move directly to the concatenation
    if extension[len(extension)-1]=="wav":
        extension[len(extension)-1] = '.mp3'
        file = ''.join(extension)        # change the last element which contains file extension from wav to mp3
        os.system("ffmpeg -i \"{0}\" -vn -ar 44100 -ac 2 -b:a 192k \"{1}\"".format(path + wav_file, path + file))

    
    if length == 0:
        length = 1
    string = ''
    index = 1
    while index<= length:
        string = string + path + file + '|'
        index = index + 1
    string = string[:len(string)-1]
    os.system("ffmpeg -i \"concat:{0}\" -acodec copy {1}".format(string, path + "output.mp3"))

def calculate_audios(audio_length: float, length: float):
    """
    This function calculates how many times an audio file will need to be self concatenated
    to fill the whole length of video file whose length is passed as a parameter
    """
    index = 1
    total_audio_length = 0
    while (total_audio_length <= length):
        total_audio_length += audio_length
        index += 1
        
    return index

def main():

    if not setup_directories():
        print("Setup Directory Failed!")
        return 0

    i = 0
    source_files = get_files("data/")
    source_audios = get_files("audio/")

    # if any of the audio or video folder is empty, the program will terminate
    if len(source_audios)==0 or len(source_files)==0:
        print("Video or Audio Files Missing!")
        return 0

    total_audios = len(source_audios)
    video_batch = []
    length = 0
    audio_file_no = 0
    video_file_no = 0
    limit = len(source_files)

    while i < limit:

        # video_batch stores the names of the files to be concatenated (batch)
        # while length stores their total duration of all files in video_batch
        video_batch, length = intake_files(i, source_files, limit)
         
        scaled_files = []
        
        i = i + len(video_batch) # increment the i by the number if files combined in the last batch

        # crop (1:1) and scale (1080x1080) all the videos in current video_batch
        for item in video_batch:
            scaled_files.append(crop_video(item, "data/", "videos/"))

        # concatenate all the scaled and cropped files
        combined_video = combine_files(scaled_files, "videos/", "videos/output/", str(video_file_no) + ".mp4")
        video_file_no += 1

        delete_temp(scaled_files, "videos/")        # delete the scaled and cropped files as they have been concatenated
        audio_required_length = 0


        # if the current audio file to be used in the list is not the last one then increment it otherwise start from the beginning
        if audio_file_no < total_audios-1:
            vid_size = video_size(source_audios[audio_file_no], "audio/")          # get the audio files's duration
            while vid_size==0.0:                                                   # if duration is 0 then something is wrong with file so try the next file
                vid_size = video_size(source_audios[audio_file_no], "audio/")
                if audio_file_no == total_audios:
                    audio_file_no = 0
                else:
                    audio_file_no += 1

            # get the required number of times audio file needs to be self-concatenated
            audio_required_length = calculate_audios(video_size(source_audios[audio_file_no], "audio/"), length)
            audio_file_no = audio_file_no + 1
        else:
            audio_file_no = 0            
            # get the required number of times audio file needs to be self-concatenated
            audio_required_length = calculate_audios(video_size(source_audios[audio_file_no], "audio/"), length)
        
        # self-concatenate the audio file the required number of times
        combine_audio(source_audios[audio_file_no], "audio/", audio_required_length)
        
        # pass the combined video file whose audio is to be replaced with the combined audio file named output.mp3
        replce_audio(combined_video, "videos/output/", "output.mp3" , "audio/")

        # delete the output.mp3 and the combined video whose audio was from the original file
        try:
            os.remove("videos/output/" + combined_video)
            os.remove("audio/output.mp3")
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()
