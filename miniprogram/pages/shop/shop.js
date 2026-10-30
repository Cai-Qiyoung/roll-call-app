const api = require('../../utils/api')

const ITEM_EMOJI = {
  free_card: '🎫',
  double_card: '🎴'
}

Page({
  data: {
    items: [],
    students: [],
    wallet: null, // 当前选中学生的积分/道具
    pickerOpen: false
  },

  onShow() {
    this.loadBase()
  },

  async loadBase() {
    try {
      const [items, students] = await Promise.all([
        api.getShopItems(),
        api.getStudents()
      ])
      this.setData({ items, students })
    } catch (e) {
      // 后端未启动时静默
    }
  },

  openPicker() {
    this.setData({ pickerOpen: true })
  },

  closePicker() {
    this.setData({ pickerOpen: false })
  },

  async selectStudent(e) {
    const no = e.currentTarget.dataset.no
    try {
      const wallet = await api.getWallet(no)
      this.setData({ wallet, pickerOpen: false })
    } catch (err) {
      wx.showToast({ title: err.message, icon: 'none' })
    }
  },

  exchange(e) {
    const code = e.currentTarget.dataset.code
    if (!this.data.wallet) {
      wx.showToast({ title: '请先在下方选择学生', icon: 'none' })
      return
    }
    api
      .exchange(this.data.wallet.student_no, code)
      .then((w) => {
        this.setData({ wallet: w })
        wx.showToast({ title: '兑换成功', icon: 'none' })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  }
})