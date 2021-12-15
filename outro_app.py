from flask import Flask, request
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
import json


'''

!! MANTEM ESSE CLOUD RUN, CRIA OUTRO A PARTIR DESSE !!

USAR ESSE PRÓPRIO CLOUD RUN PRA ENVIAR PRA AWS
AO INVÉS DE FAZER O PROPÓSITO INICIAL QUE SERIA GERAR O SPEECH-TO-TEXT


1) pega o arquivo via gs_uri = data['gs_uri'] e faz upload para o bucket S3
2) lá na AWS, vai ter uma trigger que vai gerar um Job Transcribe assim que um objeto for criado no bucket
3) o Job vai gerar o resultado em outro bucket, cria outra trigger que pega esse resultado e grava no mesmo bucket do GCP, mas apenas o SRT

'''

speech_client = speech.SpeechClient()
bucket_json = storage.Client().get_bucket('catalobyte-json')
bucket_txt = storage.Client().get_bucket('catalobyte-texto')

app = Flask(__name__)

@app.route("/", methods=["POST"])
def speechproc():

    data = request.get_json()
    gs_uri = data['gs_uri'] # uri original do 'catalobyte-output'... ou 'catalobyte-pre-speech'
    index_manticore = data['index_manticore']
    userUid = data['foldername'] # folder = firebase-uuid do front-end
    file_id = data['file_id'] # id-numerico randomico gerado no front-end e que é a Key do document no firebase arquivos/audios/
    idioma = data['idioma'];# !! APENAS PARA VERBANA, se for audiolake TEM QUE REMOVER !!

    audio = speech.RecognitionAudio(uri=gs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code=idioma,
        enable_automatic_punctuation=True,
        enable_speaker_diarization=True,
        model='default',
    )

    operation = speech_client.long_running_recognize(config=config, audio=audio)
    result = operation.result()
    texto_resp = ""
    json_saida = []
    alternative = []
    for result in result.results:
        alternative = result.alternatives[0]
        texto_resp += alternative.transcript
        texto_resp += " "
    for word_info in alternative.words:
        word = word_info.word
        start_time = word_info.start_time
        end_time = word_info.end_time
        json_saida.append({"p":word, "t": start_time.seconds, "s": start_time.total_seconds(), "e": end_time.total_seconds()})

    blob = bucket_json.blob(f'{userUid}/{index_manticore}/{file_id}.json')
    blob.upload_from_string(data=json.dumps(json_saida),content_type='application/json; charset=utf-8')
    
    blob = bucket_txt.blob(f'{userUid}/{index_manticore}/{file_id}.txt')
    blob.upload_from_string(data=texto_resp,content_type='text/plain')

    return "ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
