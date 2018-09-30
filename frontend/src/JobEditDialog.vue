<style>
.el-form-item.inline-item {
  margin-right: 1em;
  display: inline-block;
}
</style>
<template>
<el-dialog :title="title" :visible.sync="show" @close="() => this.$emit('cancel')" size="large">
  <el-form ref="form" :model="internalData" label-width="95px" >
    <el-form-item label="Name" required>
      <el-input v-model="internalData.name" :disabled="disabledFields.name"></el-input>
    </el-form-item>
    <el-form-item label="Node">
      <el-select v-model="internalData.node" clearable placeholder="Any" :disabled="disabledFields.node">
          <el-option v-for="item in nodes" :label="item.labels['kubernetes.io/hostname'] + ' (' + (item.gpu_capacity - item.gpu_used) + '/' + item.gpu_capacity + ')'"
            :value="item.labels['kubernetes.io/hostname']" :key="item.labels['kubernetes.io/hostname']">
        </el-option>
      </el-select>
      <label> (avail/total) </label>
    </el-form-item>
    <el-form-item label="GPUs" class="inline-item">
      <el-input-number v-model="internalData.gpuNum" :disabled="disabledFields.gpuNum"></el-input-number>
    </el-form-item>
    <el-form-item label="MemoryLimit" class="inline-item">
      <el-input v-model="internalData.memoryLimit" :disabled="disabledFields.memoryLimit" placeholder="NoLimit"></el-input>
    </el-form-item>
    <el-form-item label="CPULimit" class="inline-item">
      <el-input v-model="internalData.cpuLimit" :disabled="disabledFields.cpuLimit" placeholder="NoLimit"></el-input>
    </el-form-item>
    <el-form-item label="Command" required>
      <el-input type="textarea" :rows=3 v-model="internalData.command" :disabled="disabledFields.command"></el-input>
    </el-form-item>
    <el-form-item label="Image" required v-if="images && images.length < 1">
      <el-input v-model="internalData.image" />
    </el-form-item>
    <el-form-item v-else>
      <el-select v-model="internalData.image" clearable filterable  style="width: 100%;">
        <el-option v-for="item in images" :label="item" :value="item" :key="item"/>
      </el-select>
    </el-form-item>
    <el-form-item label="Repo">
      <el-autocomplete v-model="internalData.repo" :fetch-suggestions="repoQuerySearch" style="width: 100%" :disabled="disabledFields.repo"></el-autocomplete>
    </el-form-item>
    <el-form-item label="Branch">
      <el-input v-model="internalData.branch" :disabled="disabledFields.branch"></el-input>
    </el-form-item>
    <el-form-item label="Commit">
      <el-input v-model="internalData.commit" :disabled="disabledFields.commit"></el-input>
    </el-form-item>
    <el-form-item label="Comments">
      <el-input type="textarea" :rows=3 v-model="internalData.comments" :disabled="disabledFields.comments"></el-input>
    </el-form-item>
      <el-form-item label="Tags">
        <el-select v-model="internalData.tags" multiple allow-create default-first-option placeholder="" style="width: 100%;">
          <el-option v-for="item in dynamicTags" :key="item" :label="item" :value="item"></el-option>
        </el-select>
      </el-form-item>
    <el-form-item label="Auto Restart">
      <el-checkbox v-model="internalData.autoRestart" :disabled="disabledFields.autoRestart"></el-checkbox>
    </el-form-item>
    <el-form-item v-for="(volume, index) in internalData.volumeMounts" :key="volume.key" :label="'Volume'" :rules="{
        required: true, message: 'volumeMounts should not be empty', trigger: 'blur'
      }">
      <el-col :span="10">
        <el-form-item>
          <el-input placeholder="hostPath" v-model="volume.hostPath" style="width: 100%;" :disabled="disabledFields.volumeMounts"></el-input>
        </el-form-item>
      </el-col>
      <span class="inline-form-span"> </span>
      <el-col :span="10">
        <el-form-item>
          <el-input placeholder="mountPath" v-model="volume.mountPath" style="width: 100%;" :disabled="disabledFields.volumeMounts"></el-input>
        </el-form-item>
      </el-col>
      <span class="inline-form-span"> </span>
      <el-button @click.prevent="removeVolume(volume)" :disabled="disabledFields.volumeMounts">Delete</el-button>
    </el-form-item>
    <el-form-item>
      <el-button @click="addVolumeMount" :disabled="disabledFields.volumeMounts">Add volumeMounts</el-button>
    </el-form-item>
  </el-form>
  <span slot="footer" class="dialog-footer">
    <el-button @click="()=>this.$emit('cancel')">Cancel</el-button>
    <el-button type="primary" @click="() => this.$emit('confirm', this.internalData)">Confirm</el-button>
  </span>
</el-dialog>
</template>
<script>
  import {
    defaultJobData
  } from './const.js'
export default {
  name: 'job-edit-dialog',
  props: {
    nodes: {
      type: Array,
      default: []
    },
    images: {
      type: Array,
      default: []
    },
    repos: {
      type: Array,
      default: []
    },
    show: Boolean,
    title: {
      type: String,
      default: 'Edit job'
    },
    data: {
      type: Object,
      default: () => Object.assign({}, defaultJobData)
    },
    disabledFields: {
      type: Object,
      default: () => ({})
    }
  },
    data() {
    return {
        dynamicTags: [],
        value10: [],
      internalData: Object.assign({}, defaultJobData)
    }
  },
  watch: {
      data(value) {
      this.internalData = Object.assign({}, value)
    }
  },
    mounted: function () {
      this.getTags()
    },
  methods: {
      getTags: function () {
        this.$http.get('/api/tags').then((resource) => {
          this.dynamicTags = resource.body
        }).catch(() => {})
      },
    addVolumeMount: function () {
      this.data.volumeMounts.push({
        hostPath: '',
        mountPath: '',
        key: Date.now()
      })
    },
    removeVolume: function (volume) {
      var index = this.data.volumeMounts.indexOf(volume)
      if (index !== -1) {
        this.data.volumeMounts.splice(index, 1)
      }
    },
    repoQuerySearch: function (queryString, cb) {
      var repos = this.repos
      var results = queryString ? repos.filter(this.createFilter(queryString)) : repos
      console.log(results)
      cb(results)
    },
    createFilter: function (queryString) {
      return function (candidate) {
        return (candidate.value.indexOf(queryString.toLowerCase()) !== -1)
      }
    }
  }
}
</script>
        if (index !== -1) {
          this.data.volumeMounts.splice(index, 1)
        }
      },
      repoQuerySearch: function (queryString, cb) {
        var repos = this.repos
        var results = queryString ? repos.filter(this.createFilter(queryString)) : repos
        console.log(results)
        cb(results)
      },
      createFilter: function (queryString) {
        return function (candidate) {
          return (candidate.value.indexOf(queryString.toLowerCase()) !== -1)
        }
      }
    }
  }
</script>


<style>
  .el-tag {
    margin-right: 10px;
  }

  .button-new-tag {
    margin-left: 10px;
    height: 32px;
    line-height: 30px;
    padding-top: 0;
    padding-bottom: 0;
  }

  .input-new-tag {
    width: 90px;
    margin-left: 10px;
    vertical-align: bottom;
  }
</style>