#!/bin/bash

# Install system dependencies for face recognition
apt-get update
apt-get install -y \
    build-essential \
    cmake \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    python3-dev \
    python3-pip \
    libboost-python-dev \
    libboost-system-dev \
    libboost-filesystem-dev

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
