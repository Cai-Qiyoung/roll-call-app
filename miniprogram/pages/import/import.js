const api = require('../../utils/api')

Page({
  data: {
    students: []
  },

  onShow() {
    this.load()
  },

  async load() {
    try {
      const students = await api.getStudents()
      this.setData({ students })
    } catch (e) {
      // 后端未启动时静默
    }
  },

  // 从聊天记录/本地选择 Excel 或 CSV 文件导入
  chooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['xlsx', 'xls', 'csv'],
      success: (res) => {
        const file = res.tempFiles[0]
        wx.showLoading({ title: '导入中…' })
        api
          .importFile(file.path)
          .then((r) => {
            wx.hideLoading()
            wx.showToast({ title: `成功导入 ${r.imported} 人`, icon: 'none' })
            this.load()
          })
          .catch((err) => {
            wx.hideLoading()
            wx.showToast({ title: err.message || '导入失败', icon: 'none' })
          })
      }
    })
  },

  // 下载导入模板（学号、姓名、专业 + 示例行）
  downloadTemplate() {
    api.downloadTemplate().catch((err) =>
      wx.showToast({ title: err.message || '下载失败', icon: 'none' })
    )
  },

  onDelete(e) {
    const no = e.currentTarget.dataset.no
    wx.showModal({
      title: '删除学生',
      content: `确定删除 ${no} 及其点名记录吗？`,
      success: (r) => {
        if (!r.confirm) return
        api.deleteStudent(no).then(() => {
          wx.showToast({ title: '已删除', icon: 'none' })
          this.load()
        })
      }
    })
  },

  clearAll() {
    wx.showModal({
      title: '清空名单',
      content: '将删除全部学生与点名记录（顺序点名游标归零），确定？',
      success: (r) => {
        if (!r.confirm) return
        api.clearStudents().then(() => {
          wx.showToast({ title: '已清空', icon: 'none' })
          this.load()
        })
      }
    })
  }
})