# How to build Tensorflow image for KTQueue

# Build image from source(Optional)

Generally, you can use offical tensorflow package. If you want't to build your own python wheel, please refer [Installing TensorFlow from Sources](https://www.tensorflow.org/install/install_sources)

TLDR; brief procdeure to build GPU package:

configure package, enter `yes` when you are asked `Do you wish to build TensorFlow with CUDA support`

>./configure

build tensorflow

> bazel build --config=opt //tensorflow/tools/pip_package:build_pip_package

build python wheel

> bazel build --config=opt --config=cuda //tensorflow/tools/pip_package:build_pip_package

# Build docker image for KTQueue

1. copy your wheel(tensorflow-*.whl) into this directory.
2. build docker image

> docker build . -t your_image_name
