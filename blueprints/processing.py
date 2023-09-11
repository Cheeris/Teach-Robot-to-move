import openai
import time
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from exts import mongo
from google.cloud import speech
import os
from dotenv import load_dotenv
bp = Blueprint("processing",__name__, url_prefix='/processing')

load_dotenv()
def generate_output(input_text):
    # Use GPT-3.5 to generate the improved output
    commands = list(mongo.db.Command.find())
    command_names = [command["name"] for command in commands]
    name_string = ",".join(command_names)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.8,
        max_tokens=2000,
        messages=[
            {"role": "system", 
             "content": 'You will be acting as an instruction responder. \
                Then l will give you instructions in natural languages and \
                your output will be one of the following keywords '+
                name_string
                +
                'For instructions may contain more than one action key words, \
                list the one most possible keyword.\
                For actions not matching any of above keywords, reply "None"'},
            {"role": "user", "content": input_text}
        ]
    )
    print(response.choices[0].message["content"])
    return response.choices[0].message["content"]


@bp.route('/stt/whisper', methods=['POST'])
def stt():
    print('[backend] speech-to-text')
    if 'file' not in request.files:
        print('[backend] audio not in request.files')
        print(request.files['file'])
        return jsonify({'error': 'No file inside the request'})
    file = request.files['file']
    if file.filename == '':
        print('[backend] No selected file')
        return jsonify({'error': 'No selected file'})

    start_time = time.time()
    file.save("uploaded_audio.mp3")
    audiofile = open("uploaded_audio.mp3", "rb")
    transcript = openai.Audio.translate("whisper-1", audiofile)
    print(transcript['text'])
    end_time = time.time()
    stt_time = round(end_time-start_time, 2)
    print("time is " + str(stt_time))
    return jsonify({'textOutput': transcript['text'], 'time': stt_time})


@bp.route('/stt/google-cloud', methods=['POST'])
def google_stt():
    print('[backend] speech-to-text')
    if 'file' not in request.files:
        print('[backend] audio not in request.files')
        print(request.files['file'])
        return jsonify({'error': 'No file inside the request'})
    file = request.files['file']
    if file.filename == '':
        print('[backend] No selected file')
        return jsonify({'error': 'No selected file'})
    start_time = time.time()
    file.save("uploaded_audio.mp3")

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        api_key=os.getenv("GOOGLE_CLOUD_API_KEY")
    )
    with file.open("rb") as audio_file:
        content = audio_file.read()
        audio = speech.RecognitionAudio(content=content)
        response = client.recognize(config=config, audio=audio)

    transcript = response.results[0].alternatives[0].transcript
    print(transcript)
    end_time = time.time()
    stt_time = round(end_time - start_time, 2)
    print("time is " + str(stt_time))
    return jsonify({'textOutput': transcript, 'time': stt_time})


@bp.route('/generate-command', methods=['POST'])
def generate_command():
    try:
        data = request.json
        input_text = data['input_text']
        if not input_text:
            return jsonify({"error": "Please provide input text, style, and platform."}), 400

        output_text = generate_output(input_text)
        return jsonify({"output_text": output_text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route('/regenerate-command', methods=['POST'])
def regenerate_command():
    try:
        data = request.json
        input_text = data['input_text']

        if not input_text:
            return jsonify({"error": "Please provide input text, style, and platform."}), 400

        output_text = generate_output(input_text)
        return jsonify({"output_text": output_text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@bp.route('/perform-command', methods=['POST'])
def perform_command():
    command_name = request.form['Command']
    robot_command = mongo.db.Command.find_one({'name': command_name})
    print(robot_command['command'])
    if robot_command is None:
        return jsonify({'robot_command': 'report_not_exist'})
    else:
        return jsonify({'robot_command': robot_command['command']})

