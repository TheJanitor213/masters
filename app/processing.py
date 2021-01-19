from flask import Flask, Response, request, Blueprint
import logging
import boto3
import json
import os
import audioread
from pydub.silence import split_on_silence
from pydub import AudioSegment
from config import LOGGER as logger, APP as app

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG) 
processing = Blueprint('index', __name__, url_prefix='/')

FFMPEG_STATIC = "/var/task/ffmpeg"
# now call ffmpeg with subprocess
import subprocess

AudioSegment.converter = '/opt/python/ffmpeg'

@processing.before_request
def before():
    logger.info(request.url)
    logger.debug(request.__dict__)
    logger.debug(request.headers)
    logger.debug(request.get_data())


@processing.after_request
def after(response):
    logger.debug(response.status)
    logger.debug(response.get_data())
    return response


@processing.route('/upload',methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files['audio_data']
        if uploaded_file.filename != '':
            uploaded_file.save('/tmp/'+uploaded_file.filename +'.wav')
            s3 = boto3.client('s3')
            s3.upload_file('/tmp/'+ uploaded_file.filename +'.wav', 'datasets-masters-2020',uploaded_file.filename +'.wav')
        return "Success", 200
    except Exception as e:
        logger.exception(e)
        return "Error", 500


def match_target_amplitude(aChunk, target_dBFS):
    change_in_dBFS = target_dBFS - aChunk.dBFS
    return aChunk.apply_gain(change_in_dBFS)

def process_file(event, context):
    try:
        
        bucket = event['Records'][0]['s3']['bucket']['name']
        s3_client = boto3.client('s3')
        key = event['Records'][0]['s3']['object']['key']
        if key.split('/')[0] != 'splits':
        # Get the bytes from S3
            file_loc = '/tmp/' + key
            # Download this file to writable tmp space.
            logger.debug(file_loc)
            logger.debug(key)
            logger.debug(bucket)
            s3_client.download_file(bucket, key, file_loc)
            song = AudioSegment.from_wav(file_loc)
            

            chunks = split_on_silence (song, min_silence_len = 300, silence_thresh = -30)
            logger.debug(chunks)
            for i, chunk in enumerate(chunks):
                silence_chunk = AudioSegment.silent(duration=200)
                audio_chunk = silence_chunk + chunk + silence_chunk
                normalized_chunk = match_target_amplitude(audio_chunk, -20.0)
                logger.debug("Exporting chunk{0}.mp3.".format(i))
                normalized_chunk.export("/tmp/chunk{0}.mp3".format(i),bitrate = "320k",format = "mp3")
                s3_client.upload_file("/tmp/chunk{0}.mp3".format(i), 'datasets-masters-2020',"splits/{0}/chunk_{1}.mp3".format(key.split('.')[0], i))
            return "Complete"
        else:
            logger.debug('Nothing to do here')
            return

    except Exception as e:
        logger.exception(e)
        return "Error", 500
