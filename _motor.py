#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys

class Motor():
    def __init__(self, coordinate):
        self.coordinate = coordinate

    def get_coordinate(self, data):
        data['x'] = data['x'] - self.coordinate['x']
        data['y'] = data['y'] - self.coordinate['y']
        data['z'] = data['z'] - self.coordinate['z']
        return data