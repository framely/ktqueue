<template>
<el-dialog :title="title" :value="show" @close="() => this.$emit('cancel')" size="large">
  <el-form ref="form" :model="internalData" label-width="95px">
    <el-form-item label="Name" required>
      <el-input v-model="internalData.name"></el-input>
    </el-form-item>
    <el-form-item label="Node">
      <el-select v-model="internalData.node" clearable placeholder="Any">
        <el-option v-for="item in nodes" :label="item.labels['kubernetes.io/hostname'] + ' (' + (item.gpu_capacity - item.gpu_used) + '/' + item.gpu_capacity + ')'" :value="item.labels['kubernetes.io/hostname']" :key="item.labels['kubernetes.io/hostname']">
        </el-option>
      </el-select>
      <label> (avail/total) </label>
    </el-form-item>
    <el-form-item label="GPUs">
      <el-input-number v-model="internalData.gpu_num"></el-input-number>
    </el-form-item>
    <el-form-item label="Command" required>
      <el-input type="textarea" :rows=3 v-model="internalData.command"></el-input>
    </el-form-item>
    <el-form-item label="Image" required>
      <el-input v-model="internalData.image"></el-input>
    </el-form-item>
    <el-form-item label="Repo">
      <el-autocomplete v-model="internalData.repo" :fetch-suggestions="repoQuerySearch" style="width: 100%"></el-autocomplete>
    </el-form-item>
    <el-form-item label="Branch">
      <el-input v-model="internalData.branch"></el-input>
    </el-form-item>
    <el-form-item label="Commit id">
      <el-input v-model="internalData.commit_id"></el-input>
    </el-form-item>
    <el-form-item label="Comments">
      <el-input type="textarea" :rows=3 v-model="internalData.comments"></el-input>
    </el-form-item>
    <el-form-item v-for="(volume, index) in internalData.volumeMounts" :key="volume.key" :label="'Volume'" :rules="{
        required: true, message: 'volumeMounts should not be empty', trigger: 'blur'
      }">
      <el-col :span="10">
        <el-form-item>
          <el-input placeholder="hostPath" v-model="volume.hostPath" style="width: 100%;"></el-input>
        </el-form-item>
      </el-col>
      <span class="inline-form-span"> </span>
      <el-col :span="10">
        <el-form-item>
          <el-input placeholder="mountPath" v-model="volume.mountPath" style="width: 100%;"></el-input>
        </el-form-item>
      </el-col>
      <span class="inline-form-span"> </span>
      <el-button @click.prevent="removeVolume(volume)">删除</el-button>
    </el-form-item>
    <el-form-item>
      <el-button @click="addVolumeMount">Add volume</el-button>
    </el-form-item>
  </el-form>
  <span slot="footer" class="dialog-footer">
    <el-button @click="()=>this.$emit('cancel')">取 消</el-button>
    <el-button type="primary" @click="() => this.$emit('confirm', this.internalData)">确 定</el-button>
  </span>
</el-dialog>
</template>
<script>
import { defaultJobData } from './const.js'
export default {
  name: 'job-edit-dialog',
  props: {
    nodes: {
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
    }
  },
  data () {
    return {
      internalData: Object.assign({}, defaultJobData)
    }
  },
  watch: {
    data (value) {
      this.internalData = Object.assign({}, value)
    }
  },
  methods: {
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
