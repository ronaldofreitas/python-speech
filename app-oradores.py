from flask import Flask, request
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
import json

speech_client = speech.SpeechClient()
bucket_json = storage.Client().get_bucket('catalobyte-json')
bucket_txt = storage.Client().get_bucket('catalobyte-texto')

app = Flask(__name__)

@app.route("/", methods=["POST"])
def speechproc():

    data = request.get_json()
    gs_uri = data['gs_uri']
    index_manticore = data['index_manticore']
    userUid = data['foldername'] # folder = firebase-uuid do front-end
    file_id = data['file_id'] # id-numerico randomico gerado no front-end e que é a Key do document no firebase arquivos/audios/
    
    # catalobyte-output/elrQVvaWHGbtkhXxg2BOHcm01TR2/Udsaj345f4gf/016792521970558816

    audio = speech.RecognitionAudio(uri=gs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="pt-BR",
        enable_speaker_diarization=True,
        enable_automatic_punctuation=True,
        diarization_speaker_count=2,
        model='default',
    )

    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    result = response.results[-1]
    words_info = result.alternatives[0].words

    texto_resp = ""
    for r in response.results:
        texto_resp += r.alternatives[0].transcript
        texto_resp += " "

    json_saida = []
    for word_info in words_info:
        json_saida.append({"p":word_info.word, "o": word_info.speaker_tag, "t": word_info.start_time.seconds})

    blob = bucket_json.blob(f'{userUid}/{index_manticore}/{file_id}.json')
    blob.upload_from_string(data=json.dumps(json_saida),content_type='application/json; charset=utf-8')
    
    blob = bucket_txt.blob(f'{userUid}/{index_manticore}/{file_id}.txt')
    blob.upload_from_string(data=texto_resp,content_type='text/plain')

    return "ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
