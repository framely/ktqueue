# Deployment

- mongodb-service.yaml
- mongodb-dev.yaml
- mongodb-production.yaml

# modify configure

> cp mongodb-production.yaml dep-mongodb-production.yaml

update your own ceph configure

if you want to know mon in your ceph cluster, just type

> ceph mon stat

get your ceph-secret to kubernetes

> sudo ceph auth get-key client.admin | base64

Note: though ceph get-key is encoded by base64, you should encode it again.

then, update your ceph-secret.yaml, and import `ceph-secret.yaml`

> cp ceph-secret.yaml dep-ceph-secret.yaml && vi dep-ceph-secret.yaml
> kubectl create -f dep-ceph-secret.yaml

# create rbd

> rbd create rbd/ktqueue-mongodb -s 10240

> rbd info rbd/ktqueue-mongodb

try:

> rbd map ktqueue-mongodb

current linux kernal doesn't support all the features. if you get error, refer [this](http://tonybai.com/2016/11/07/integrate-kubernetes-with-ceph-rbd/)
> rbd feature disable ktqueue-mongodb exclusive-lock, object-map, fast-diff, deep-flatten

# create services


create mongodb service

> kubectl create -f mongodb-service.yaml

create mongodb server

> kubectl create -f dep-mongodb-production.yaml
