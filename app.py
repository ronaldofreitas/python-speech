from flask import Flask, request
import srt
from google.cloud import speech
#from google.cloud import speech_v1
#from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
#import json
import datetime

'''
https://stackoverflow.com/questions/54271749/error-with-enable-speaker-diarization-tag-in-google-cloud-speech-to-text?rq=1

The enable_speaker_diarization=True parameter in speech.types.RecognitionConfig is available only in the library speech_v1p1beta1 at the moment, 
so, you need to import that library in order to use that parameter, not the default speech one. 
I did some modifications to your code and works fine for me. Take into account that you need to use a service account to run this code.
'''

def long_running_recognize(storage_uri, idioma):
    client = speech.SpeechClient()
    config = {
        "language_code": idioma,
        "sample_rate_hertz": 16000,
        #"encoding": enums.RecognitionConfig.AudioEncoding.LINEAR16,
        "encoding": "FLAC",
        "audio_channel_count": 1,
        "enable_word_time_offsets": True,
        #"model": "video",
        "enable_automatic_punctuation":True
    }
    audio = {"uri": storage_uri}
    operation = client.long_running_recognize(config, audio)
    response = operation.result()
    return response

def subtitle_generation(response):
    bin_size=3
    """We define a bin of time period to display the words in sync with audio. 
    Here, bin_size = 3 means each bin is of 3 secs. 
    All the words in the interval of 3 secs in result will be grouped togather."""
    transcriptions = []
    index = 0
 
    for result in response.results:
        try:
            if result.alternatives[0].words[0].start_time.seconds:
                # bin start -> for first word of result
                start_sec = result.alternatives[0].words[0].start_time.seconds 
                start_microsec = result.alternatives[0].words[0].start_time.nanos * 0.001
            else:
                # bin start -> For First word of response
                start_sec = 0
                start_microsec = 0 
            end_sec = start_sec + bin_size # bin end sec
            
            # for last word of result
            last_word_end_sec = result.alternatives[0].words[-1].end_time.seconds
            last_word_end_microsec = result.alternatives[0].words[-1].end_time.nanos * 0.001
            
            # bin transcript
            transcript = result.alternatives[0].words[0].word
            
            index += 1 # subtitle index

            for i in range(len(result.alternatives[0].words) - 1):
                try:
                    word = result.alternatives[0].words[i + 1].word
                    word_start_sec = result.alternatives[0].words[i + 1].start_time.seconds
                    word_start_microsec = result.alternatives[0].words[i + 1].start_time.nanos * 0.001 # 0.001 to convert nana -> micro
                    word_end_sec = result.alternatives[0].words[i + 1].end_time.seconds
                    word_end_microsec = result.alternatives[0].words[i + 1].end_time.nanos * 0.001

                    if word_end_sec < end_sec:
                        transcript = transcript + " " + word
                    else:
                        previous_word_end_sec = result.alternatives[0].words[i].end_time.seconds
                        previous_word_end_microsec = result.alternatives[0].words[i].end_time.nanos * 0.001
                        
                        # append bin transcript
                        transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, previous_word_end_sec, previous_word_end_microsec), transcript))
                        
                        # reset bin parameters
                        start_sec = word_start_sec
                        start_microsec = word_start_microsec
                        end_sec = start_sec + bin_size
                        transcript = result.alternatives[0].words[i + 1].word
                        
                        index += 1
                except IndexError:
                    pass
            # append transcript of last transcript in bin
            transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, last_word_end_sec, last_word_end_microsec), transcript))
            index += 1
        except IndexError:
            pass
    
    subtitles = srt.compose(transcriptions)
    return subtitles


bucket_sub = storage.Client().get_bucket('verbana_subs')
app = Flask(__name__)
@app.route("/", methods=["POST"])
def speechproc():

    data = request.get_json()
    gs_uri = data['gs_uri'] # uri original do 'catalobyte-output'... ou 'catalobyte-pre-speech'
    index_manticore = data['index_manticore']
    userUid = data['foldername'] # folder = firebase-uuid do front-end
    file_id = data['file_id'] # id-numerico randomico gerado no front-end e que é a Key do document no firebase arquivos/audios/
    idioma = data['idioma']
    trad_idom = data['idiotrad']
    storage_uri = gs_uri #"gs://catalobyte-output/1sPcgixNZobTGi1McrKK7UyaZUd2/o6h0z2g9c7/8445869181/1636311108576.flac"

    response = long_running_recognize(storage_uri, idioma)
    subtitles = subtitle_generation(response)

    blob = bucket_sub.blob(f'{userUid}/{index_manticore}/{file_id}.srt')
    blob.upload_from_string(data=subtitles, content_type='application/x-subrip')
    blob.metadata = {'x-goog-meta-is-new': 'true', 'x-goog-meta-item-trad': trad_idom}
    blob.patch()

    return "ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
