<template>
  <el-container style="height: 100vh; display: flex; flex-direction: column;">
    <el-header style="padding: 0;">
      <div class="header-content">
        <h1 class="logo">视频字幕生成器</h1>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          :router="true"
          class="top-menu"
          background-color="#409eff"
          text-color="#fff"
          active-text-color="#ffd04b"
        >
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/progress">进度</el-menu-item>
          <el-menu-item index="/history">历史记录</el-menu-item>
          <el-menu-item index="/settings">设置</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}
.el-header {
  background-color: #409eff;
  height: 60px !important;
}
.header-content {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0 20px;
}
.logo {
  color: #fff;
  font-size: 20px;
  white-space: nowrap;
  margin-right: 40px;
}
.top-menu {
  border-bottom: none !important;
  flex: 1;
}
.top-menu .el-menu-item {
  font-size: 15px;
}
.top-menu .el-menu-item:hover {
  background-color: #66b1ff !important;
}
.main-content {
  background-color: #f5f7fa;
  flex: 1;
  overflow-y: auto;
}
</style>
