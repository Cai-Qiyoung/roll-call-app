const api = require('../../utils/api')

Page({
  data: {
    mode: 'random', // random 随机点名 | sequence 按学号顺序
    thursday: false, // 模拟疯狂星期四开关（周四当天自动生效）
    students: [], // 名单缓存（动画轮播 + 转移人选）
    rolling: false,
    showName: '', // 动画中滚动的名字
    picked: null, // 当前被点到的学生（含 event/boosted 等）
    scoreOpen: false, // 答题计分弹层
    transferOpen: false, // 转移弹层
    repeatOptions: [
      { v: 0.5, label: '准确重复 +0.5' },
      { v: -1, label: '未能重复 -1' },
      { v: 0, label: '不适用' }
    ],
    answerOptions: [0.5, 1, 1.5, 2, 2.5, 3, 0],
    repeat: 0,
    answer: 0,
    useDoubleCard: false
  },

  onShow() {
    this.fetchStudents()
  },

  async fetchStudents() {
    try {
      const students = await api.getStudents()
      this.setData({ students })
    } catch (e) {
      // 后端未启动时静默，点名时会再提示
    }
  },

  switchMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode })
  },

  onThursday(e) {
    this.setData({ thursday: e.detail })
  },

  // 点名：先播滚动动画，动画期间请求后端，结束后揭晓结果
  startRoll() {
    if (this.data.rolling) return
    const names = this.data.students.map((s) => s.name)
    if (!names.length) {
      wx.showToast({ title: '名单为空，请先到「名单」页导入', icon: 'none' })
      return
    }
    this.setData({ picked: null, rolling: true, showName: '' })
    const begin = Date.now()
    const DURATION = 1400
    const timer = setInterval(() => {
      this.setData({
        showName: names[Math.floor(Math.random() * names.length)]
      })
      if (Date.now() - begin >= DURATION) {
        clearInterval(timer)
        this.setData({ rolling: false })
      }
    }, 60)

    const fn =
      this.data.mode === 'random'
        ? api.randomRoll(this.data.thursday)
        : api.sequenceRoll()
    fn.then((picked) => this.setData({ picked })).catch((err) => {
      clearInterval(timer)
      this.setData({ rolling: false })
      wx.showToast({ title: err.message || '点名失败', icon: 'none' })
    })
  },

  // 到场 +1（双倍事件 x2）
  attendTo() {
    const picked = this.data.picked
    if (!picked || picked.handled) return
    api
      .confirmRoll({ student_no: picked.student_no, attend: true, event: picked.event })
      .then((res) => {
        const done = { ...res, event: picked.event, boosted: picked.boosted, handled: true }
        this.setData({ picked: done })
        wx.showToast({ title: `到场 +${res.delta} 分（当前 ${res.score} 分）`, icon: 'none' })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  },

  // 缺席：不加分，仅记录
  absentTo() {
    const picked = this.data.picked
    if (!picked || picked.handled) return
    api
      .confirmRoll({ student_no: picked.student_no, attend: false })
      .then((res) => {
        this.setData({
          picked: { ...res, event: picked.event, boosted: picked.boosted, handled: true }
        })
        wx.showToast({ title: '已记录缺席', icon: 'none' })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  },

  // 免点券：豁免本轮
  useFreeCard() {
    const picked = this.data.picked
    if (!picked || picked.handled) return
    api
      .confirmRoll({ student_no: picked.student_no, attend: true, use_free_card: true })
      .then((res) => {
        this.setData({
          picked: { ...res, event: picked.event, boosted: picked.boosted, handled: true }
        })
        wx.showToast({ title: '免点券已使用，本轮豁免', icon: 'none' })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  },

  // 转移权：转给其他同学
  openTransfer() {
    const picked = this.data.picked
    if (!picked || picked.handled) return
    if (picked.transfer_tokens <= 0) {
      wx.showToast({ title: '该同学没有转移权', icon: 'none' })
      return
    }
    this.setData({ transferOpen: true })
  },

  doTransfer(e) {
    const picked = this.data.picked
    const to = e.currentTarget.dataset.no
    api
      .transfer(picked.student_no, to)
      .then((res) => {
        this.setData({
          transferOpen: false,
          picked: { ...res.to, event: picked.event, thursday: picked.thursday, boosted: false }
        })
        wx.showToast({ title: `已转移给 ${res.to.name}`, icon: 'none' })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  },

  closeTransfer() {
    this.setData({ transferOpen: false })
  },

  // 答题计分弹层
  openScore() {
    if (!this.data.picked) return
    this.setData({ scoreOpen: true, repeat: 0, answer: 0, useDoubleCard: false })
  },

  closeScore() {
    this.setData({ scoreOpen: false })
  },

  setRepeat(e) {
    this.setData({ repeat: e.currentTarget.dataset.v })
  },

  setAnswer(e) {
    this.setData({ answer: e.currentTarget.dataset.v })
  },

  toggleDoubleCard() {
    this.setData({ useDoubleCard: !this.data.useDoubleCard })
  },

  submitScore() {
    const picked = this.data.picked
    const delta = (this.data.repeat || 0) + (this.data.answer || 0)
    if (!delta) {
      wx.showToast({ title: '请先选择一个计分项', icon: 'none' })
      return
    }
    api
      .scoreAnswer({
        student_no: picked.student_no,
        delta,
        event: picked.event,
        use_double_card: this.data.useDoubleCard
      })
      .then((res) => {
        this.setData({
          scoreOpen: false,
          picked: { ...res, event: picked.event, boosted: picked.boosted, handled: true }
        })
        wx.showToast({
          title: `本次 ${res.delta > 0 ? '+' : ''}${res.delta}（当前 ${res.score} 分）`,
          icon: 'none'
        })
      })
      .catch((err) => wx.showToast({ title: err.message, icon: 'none' }))
  }
})