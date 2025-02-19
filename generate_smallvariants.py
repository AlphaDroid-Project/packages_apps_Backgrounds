#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import os

from PIL import Image

path = os.path.dirname(os.path.realpath(__file__))

resources = ["res/drawable-nodpi"]

def generate_smallvariants(resource):
    global path
    wallpapers_path = os.path.join(path, resource)
    clean(wallpapers_path)
    wallpapers = os.listdir(wallpapers_path)

    for wallpaper in wallpapers:
        # Append _small.png to the wallpaper
        wallpaper_small = os.path.splitext(wallpaper)[0] + "_small.png"
        wallpaper_small_path = os.path.join(wallpapers_path, wallpaper_small)

        # Save the wallpaper with 1/2 size to wallpaper_small_path
        with Image.open(os.path.join(wallpapers_path, wallpaper)) as img:
            size = int(img.width / 2), int(img.height / 2)

            img_small = img.resize(size, Image.Resampling.LANCZOS)
            img_small.save(wallpaper_small_path, "PNG")

def clean(wallpapers_path):
    wallpapers = os.listdir(wallpapers_path)

    for wallpaper in wallpapers:
        # Get rid of existing small variants
        if wallpaper.endswith("_small.png"):
            os.remove(os.path.join(wallpapers_path, wallpaper))

for resource in resources:
    generate_smallvariants(resource)
