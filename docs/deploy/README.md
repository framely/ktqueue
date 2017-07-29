# Deployment

# Brief

1. setup kubernetes and ceph cluster
2. add ceph-secret to kubernetes
3. deploy mongodb based on kubernetes and ceph
4. build ktqueue docker image
5. deploy ktqueue

To setup a KTQueue node, please read [How to setup a KTQueue node](./NODE.md)


# File list

- ktqueue.yaml
- mongodb-service.yaml
- mongodb-dev.yaml
- mongodb-production.yaml

# Dependancy

ktqueue requires kubernetes and cephfs, make sure you already have them.

# Prepare ceph

kubernetes and other components needs permission (aka, a secret) to access ceph.

if you want to know mons in your ceph cluster, just type:

> ceph mon stat

then, get your ceph-secret to kubernetes

> sudo ceph auth get-key client.admin | base64

Note: though `ceph get-key`'s response is encoded by base64, you should encode it again.

then, update your ceph-secret.yaml, add your secret after `key:`

> cp ceph-secret.yaml dep-ceph-secret.yaml && vi dep-ceph-secret.yaml  

and import `ceph-secret.yaml`

> kubectl create -f dep-ceph-secret.yaml

# Deploy mongodb

## create rbd

mongodb needs a `persistent volume`(just like a disk) to store data. so you should create one.

> rbd create rbd/ktqueue-mongodb -s 10240

> rbd info rbd/ktqueue-mongodb

try:

> rbd map ktqueue-mongodb

current linux kernal doesn't support all the features. if you get error, refer [this](http://tonybai.com/2016/11/07/integrate-kubernetes-with-ceph-rbd/)

> rbd feature disable ktqueue-mongodb exclusive-lock, object-map, fast-diff, deep-flatten

## Create mongodb services

> cp mongodb-production.yaml dep-mongodb-production.yaml

create mongodb service

> kubectl create -f mongodb-service.yaml

create mongodb server

> kubectl create -f dep-mongodb-production.yaml

# Deploy ktqueue

## mount cephfs
ktqueue dameon needs to access ceph to clone code, store log, etc. and ktqueue job needs to access ceph to store output.

so you should ensure that cephfs has been mounted at `/mnt/cephfs` on ensure every single node you want to run ktqueue jobs or ktqueue dameon.

you should modify `fstab` and add cephfs mount.

## build image

build front-end

> cd frontend  
> npm install  
> npm run build  

build docker image

> docker build -t ktqueue .

you can modify `dep-ktqueue.yaml`(see next step)and change image name if you want.


## deploy

> cp ktqueue.yaml dep-ktqueue.yaml

if you want to change IP/port of ktqueue or assign ktqueue to a specific node, you should modify `dep-ktqueue.yaml`

to select node you want to run ktqueue, change `host_name_you_want` after `kubernetes.io/hostname` and uncomment this line.

to select IP/port, change `ip_you_want_to_access_form_outside` under `externalIPs`

finish it:

> kubectl create -f dep-ktqueue.yaml

enjoy!
