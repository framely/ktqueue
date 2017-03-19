# How to setup a KTQueue node

## Brief

1. join the kubernetes cluster, and ensure `kubelet`'s GPU support is enabled.
2. mount the cephfs on `/mnt/cephfs`
3. install `nvidia-docker` and run it once

## GPU support of kubelet

Kubernetes (> v1.6.0-beta.1) is supporting multi-GPU now, please follow the newest guide to enable GPU support.

## Nvidia-Docker

[nvidia-docker](https://github.com/NVIDIA/nvidia-docker) homepage

CUDA in container need NVIDIA drivers such as `libcuda.so.1` to work. And KTQueue assume that drivers  located at `/var/lib/nvidia-docker/volumes/nvidia_driver/`. So you need to install nvidia-docker and use nvidia-docker to run a cuda image to ensure that the drivers are located in the right place.

1. follow the installation instruction to install nvidia-docker
2. run the test nvidia-smi with nvidia-docker
3. make sure that there is a driver like `367.57` are located at `/var/lib/nvidia-docker/volumes/nvidia_driver/`

## Trouble shoot

- nvidia-smi print the right output, but there are no drivers found at `/var/lib/nvidia-docker/volumes/nvidia_driver/`

try to update the nvidia-docker(>1.0.0), and check docker volumes

> docker volume ls

you may get a line like  

```
DRIVER              VOLUME NAME
nvidia-docker       nvidia_driver_367.57
```

try to remove that volume and run `nvidia-docker run --rm nvidia/cuda nvidia-smi` again.
