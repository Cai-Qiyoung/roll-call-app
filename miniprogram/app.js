App({
  onLaunch() {
    // 启动时登录（微信登录换取后端 token）
    this.login()
  },

  login() {
    wx.login({
      success: (res) => {
        const api = require('./utils/api')
        api.login(res.code).then((data) => {
          this.globalData.token = data.token
          wx.setStorageSync('token', data.token)
        }).catch(() => {
          // 后端未启动时静默失败，开发阶段可忽略
        })
      }
    })
  },

  globalData: {
    token: ''
  }
})