# -*- coding: utf-8 -*-
"""rock_paper_scissor_demo.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1dGoRrcQMbxKCcAknt8x7-ONiZcdbnmxo
"""

#!/usr/bin/env python3
#
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Script to run generic MobileNet based classification model."""
import argparse
import collections
import contextlib
import io
import logging
import math
import os
import queue
import signal
import sys
import threading
import time
import random


from PIL import Image, ImageDraw, ImageFont

from aiy.board import Board
from aiy.leds import Color, Leds, Pattern, PrivacyLed
from aiy.toneplayer import TonePlayer
from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from aiy.vision.streaming.server import StreamingServer
from aiy.vision.streaming import svg
from picamera import PiCamera, Color

from aiy.vision import inference
from aiy.vision.models import utils
from gpiozero import Servo
from aiy.pins import (PIN_A)

servo = Servo(PIN_A)


# global var
states = ['rock', 'paper', 'scissor', 'undefined']
player_state = states[3]
comp_state = states[3]
def read_labels(label_path):
    with open(label_path) as label_file:
        return [label.strip() for label in label_file.readlines()]


def get_message(result, threshold, top_k):
    if result:
        return 'Detecting:\n %s' % '\n'.join(result)

    return 'Nothing detected when threshold=%.2f, top_k=%d' % (threshold, top_k)


def process(result, labels, tensor_name, threshold, top_k):
    """Processes inference result and returns labels sorted by confidence."""
    # MobileNet based classification model returns one result vector.
    assert len(result.tensors) == 1
    tensor = result.tensors[tensor_name]
    probs, shape = tensor.data, tensor.shape
    assert shape.depth == len(labels)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:top_k]
    return [' %s (%.2f)' % (labels[index], prob) for index, prob in pairs]

def set_user_state(state):
    global player_state
    if state == 'rock':
        player_state = states[0]
    elif state == 'paper':
        player_state = states[1]
    elif state == 'scissor':
        player_state = states[2]
    else:
        player_state = states[3]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', required=True,
        help='Path to converted model file that can run on VisionKit.')
    parser.add_argument('--label_path', required=True,
        help='Path to label file that corresponds to the model.')
    parser.add_argument('--input_height', type=int, required=True, help='Input height.')
    parser.add_argument('--input_width', type=int, required=True, help='Input width.')
    parser.add_argument('--input_layer', required=True, help='Name of input layer.')
    parser.add_argument('--output_layer', required=True, help='Name of output layer.')
    parser.add_argument('--num_frames', type=int, default=None,
        help='Sets the number of frames to run for, otherwise runs forever.')
    parser.add_argument('--input_mean', type=float, default=128.0, help='Input mean.')
    parser.add_argument('--input_std', type=float, default=128.0, help='Input std.')
    parser.add_argument('--input_depth', type=int, default=3 , help='Input depth.')
    parser.add_argument('--threshold', type=float, default=0.1,
        help='Threshold for classification score (from output tensor).')
    parser.add_argument('--top_k', type=int, default=3, help='Keep at most top_k labels.')
    parser.add_argument('--preview', action='store_true', default=False,
        help='Enables camera preview in addition to printing result to terminal.')
    parser.add_argument('--show_fps', action='store_true', default=False,
        help='Shows end to end FPS.')
    parser.add_argument('--num_games', type=int, default=10, help='number of games.')
    args = parser.parse_args()

    model = inference.ModelDescriptor(
        name='mobilenet_based_classifier',
        input_shape=(1, args.input_height, args.input_width, args.input_depth),
        input_normalizer=(args.input_mean, args.input_std),
        compute_graph=utils.load_compute_graph(args.model_path))
    labels = read_labels(args.label_path)


    
    with PiCamera(sensor_mode=4, resolution=(1640, 1232), framerate=30) as camera:
        if args.preview:
            camera.start_preview()

        with inference.CameraInference(model) as camera_inference, \
            contextlib.ExitStack() as stack:
            board = stack.enter_context(Board())
            leds = stack.enter_context(Leds())
            for game_index in range(args.num_games):
                print('entering game number [' + str(game_index) + ']')
                for result in camera_inference.run(args.num_frames):
                    tensor = result.tensors[args.output_layer]
                    probs= tensor.data
                    pairs = [pair for pair in enumerate(probs) if pair[1] > args.threshold]
                    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
                    pair = pairs[0]
                    detected_state = labels[pair[0]]
                    board.button.wait_for_press()
                    board.button.when_pressed = set_user_state(detected_state)
                    print('player state is ' + player_state)
                    global comp_state
                    comp_state_init = random.uniform(0, 1)
                    if comp_state_init < 1/3:
                        comp_state = states[0]
                        print('computer rock')
                        servo.min()
                    elif comp_state_init >= 1/3 and comp_state_init < 2/3:
                        comp_state = states[1]
                        print('computer paper')
                        servo.mid()
                    elif comp_state_init >= 2/3:
                        comp_state = states[2]
                        print('computer scissor')
                        servo.max()
                    else:
                        comp_state = states[3]
                        print('computer undefined')
                    
                    time.sleep(1.0)
                    camera.annotate_foreground = Color('black')
                    camera.annotate_background = Color('white')
                    message
                    if player_state == comp_state:
                        print('game result: tie')
                        leds.update(Leds.rgb_on((255, 255, 0)))
                        if player_state == "rock":
                            global message 
                            message = "player: rock; computer: rock; tie"
                        if player_state == "scissor":
                            global message 
                            message = "player: scissor; computer: scissor; tie"
                        if player_state == "paper":
                            global message 
                            message = "player: paper; computer: paper; tie"
                    elif player_state == "rock":
                        if comp_state == "scissor":
                            print("game result: player wins")
                            leds.update(Leds.rgb_on((0, 255, 0)))
                            global message 
                            message = "player: rock; computer: scissor; player wins"
                        else:
                            print("game result: player loses")
                            leds.update(Leds.rgb_on((255, 0, 0)))
                            global message 
                            message = "player: rock; computer: paper; player loses"
                    elif player_state == "paper":
                        if comp_state == "rock":
                            print("game result: player wins")
                            leds.update(Leds.rgb_on((0, 255, 0)))
                            global message 
                            message = "player: paper; computer: rock; player wins"
                        else:
                            print("game result: player loses")
                            leds.update(Leds.rgb_on((255, 0, 0)))
                            global message 
                            message = "player: paper; computer: scissor; player loses"
                    elif player_state == "scissor":
                        if comp_state == "paper":
                            print("game result: player wins")
                            leds.update(Leds.rgb_on((0, 255, 0)))
                            global message 
                            message = "player: scissor; computer: paper; player wins"
                        else:
                            print("game result: player loses")
                            leds.update(Leds.rgb_on((255, 0, 0)))
                            global message 
                            message = "player: scissor; computer: rock; player loses"
                    camera.annotate_text = '\n %s' % message.encode('ascii', 'backslashreplace').decode('ascii')
                    board.button.wait_for_press()
                    leds.update(Leds.rgb_off())

                    # processed_result = process(result, labels, args.output_layer,
                    #                         args.threshold, args.top_k)
                    # message = get_message(processed_result, args.threshold, args.top_k)
                    # if args.show_fps:
                    #     message += '\nWith %.1f FPS.' % camera_inference.rate
                    # print(message)

                    # if args.preview:
                    #     camera.annotate_foreground = Color('black')
                    #     camera.annotate_background = Color('white')
                    #     # PiCamera text annotation only supports ascii.
                    #     camera.annotate_text = '\n %s' % message.encode(
                    #         'ascii', 'backslashreplace').decode('ascii')

        if args.preview:
            camera.stop_preview()


if __name__ == '__main__':
    main()