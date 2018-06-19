<template>
    <div class="box">
        <el-card v-for="(v, k) in data" :key="k" class="box-card">
            <div slot="header">
                <span>{{ v.hostname }}</span>
            </div>
            <div>
                <div class="table-box">
                    <el-table :data="v.hw" style="width: 35%" class="table-box-e">
                        <el-table-column prop="name" label="Name" width="auto">
                        </el-table-column>
                        <el-table-column prop="total" label="Total" width="auto">
                        </el-table-column>
                        <el-table-column prop="percent" label="Percent" width="90px">
                        </el-table-column>
                    </el-table>
                    <el-table :data="v.nvidia.jobs" class="table-box-e">
                        <el-table-column prop="name" label="Pid" width="75px">
                        </el-table-column>
                        <el-table-column prop="cpu" label="CpuUser" width="110px">
                        </el-table-column>
                        <el-table-column prop="memory" label="MemRSS" width="100px">
                        </el-table-column>
                        <el-table-column prop="drivers_name" label="DName" width="180px">
                        </el-table-column>
                        <el-table-column prop="drivers_temp" label="DTemp" width="88px">
                        </el-table-column>
                        <el-table-column prop="drivers_pwr" label="DPwr" width="150px">
                        </el-table-column>
                        <el-table-column prop="drivers_mem" label="DMem" width="200px">
                        </el-table-column>
                        <el-table-column prop="drivers_util" label="DUtil">
                        </el-table-column>
                    </el-table>
                </div>
            </div>
        </el-card>
    </div>
</template>

<script>
    export default {
        data: function () {
            return {
                wscon: null,
                data: {},
            }
        },

        mounted: function () {
            this.startWS()
        },

        methods: {
            startWS: function () {
                let schema = window.location.protocol.startsWith('https') ? 'wss://' : 'ws://'
                let url = schema + window.location.host + '/wsapi/monitor/sub/all/'
                let con = new WebSocket(url)

                let onmessage = message => {
                    let d = JSON.parse(message.data)
                    this.$set(this.data, d.hostname, d)
                }
                let onerror = data => {
                    console.error(data)
                }
                let onclose = data => {
                    console.error(data)
                }

                con.close = onclose
                con.onerror = onerror
                con.onmessage = onmessage
            }
        }
    }
</script>

<style>
    .box {
        font-size: 16px;
        margin-top: 20px;
        border: 1px solid #dfe6ec;
    }

    .table-box {
        display: flex;
    }

    .table-box-e {
        margin: 5px;
    }

    .clearfix {
        padding: 6px 10px;
    }

    .box-card {
        margin: 20px;
    }

  .demo-table-expand label {
    width: 90px;
    color: #99a9bf;
  }
  .demo-table-expand .el-form-item {
    margin-right: 0;
    margin-bottom: 0;
  }
</style>