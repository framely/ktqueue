const defaultJobData = {
    name: '',
    node: null,
    gpuNum: 0,
    command: '',
    image: '',
    repo: '',
    branch: '',
    commit: '',
    comments: '',
    volumeMounts: [],
    cpuLimit: '1.5',
    memoryLimit: '2Gi',
    autoRestart: false,
    tags: []
}
export {
    defaultJobData
}