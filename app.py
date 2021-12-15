from flask import Flask, request
import srt
from google.cloud import speech
#from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
#import json

def long_running_recognize(storage_uri, idioma):
    client = speech.SpeechClient()

    operation = client.long_running_recognize(
        config = {
            "enable_word_time_offsets": True,
            "enable_automatic_punctuation": True,
            "sample_rate_hertz": 16000,
            "language_code": idioma,
            "audio_channel_count": 1,
            "encoding": "FLAC",
        },
        audio={
            "uri": storage_uri
        },
    )
    response = operation.result()
    subs = []
    for result in response.results:
        # First alternative is the most probable result
        subs = break_sentences(40, subs, result.alternatives[0])

    return subs


def break_sentences(max_chars, subs, alternative):
    firstword = True
    charcount = 0
    idx = len(subs) + 1
    content = ""

    for w in alternative.words:
        if firstword:
            # first word in sentence, record start time
            start = w.start_time.ToTimedelta()

        charcount += len(w.word)
        content += " " + w.word.strip()

        if ("." in w.word or "!" in w.word or "?" in w.word or
                charcount > max_chars or
                ("," in w.word and not firstword)):
            # break sentence at: . ! ? or line length exceeded
            # also break if , and not first word
            subs.append(srt.Subtitle(index=idx,
                                     start=start,
                                     end=w.end_time.ToTimedelta(),
                                     content=srt.make_legal_content(content)))
            firstword = True
            idx += 1
            content = ""
            charcount = 0
        else:
            firstword = False
    return subs


def write_srt(subs):
    srt_file = "legenda.srt"
    f = open(srt_file, 'w')
    f.writelines(srt.compose(subs))
    f.close()
    return


def write_txt(subs):
    txt_file = "texto.txt"
    f = open(txt_file, 'w')
    for s in subs:
        f.write(s.content.strip() + "\n")
    f.close()
    return


speech_client = speech.SpeechClient()
#bucket_json = storage.Client().get_bucket('catalobyte-json')
#bucket_txt = storage.Client().get_bucket('catalobyte-texto')
bucket_sub = storage.Client().get_bucket('verbana_subs')

app = Flask(__name__)

@app.route("/", methods=["POST"])
def speechproc():

    data = request.get_json()
    gs_uri = data['gs_uri'] # uri original do 'catalobyte-output'... ou 'catalobyte-pre-speech'
    index_manticore = data['index_manticore']
    userUid = data['foldername'] # folder = firebase-uuid do front-end
    file_id = data['file_id'] # id-numerico randomico gerado no front-end e que é a Key do document no firebase arquivos/audios/
    idioma = data['idioma'];# !! APENAS PARA VERBANA, se for audiolake TEM QUE REMOVER !!

    storage_uri = gs_uri #"gs://catalobyte-output/1sPcgixNZobTGi1McrKK7UyaZUd2/o6h0z2g9c7/8445869181/1636311108576.flac"
    idioma = idioma #"pt-BR"
    subs = long_running_recognize(storage_uri, idioma)
    #write_srt(subs)
    #write_txt(subs)

    '''
    srt_file = "legenda.srt"
    f = open(srt_file, 'w')
    f.writelines(srt.compose(subs))
    f.close()
    '''

    blob = bucket_sub.blob(f'{userUid}/{index_manticore}/{file_id}.srt')
    blob.upload_from_string(data=srt.compose(subs), content_type='text/plain')

    '''
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
    '''

    return "ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
