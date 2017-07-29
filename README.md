# KTQueue

kubernetes task queue with GPU support

# Features

- support GPU tasks
- support assigning the task to node manually
- realtime logs on webpage & log version management
- mount host-path to Pod manually
- Tensorboard manage & proxy
- git clone repository with ssh-key or username & password or Github OAuth
- CPU & Memory limit supported

# screenshoot

![screenshoot](https://user-images.githubusercontent.com/1068203/28708229-10e6e19e-73ae-11e7-882f-f4fb6bff877a.png)

# How to deploy

deployment guide under [deploy](./docs/deploy) directory

# How to build images for KTQueue

You can use any framework you want as long as you have the correct docker image, here are examples to build docker image for KTQueue

- [tensorflow](./docs/docker_image_example/tensorflow)
