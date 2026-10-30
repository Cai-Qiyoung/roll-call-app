const api = require('../../utils/api')

Page({
  data: {
    list: [],
    stats: {},
    medals: ['🥇', '🥈', '🥉']
  },

  onShow() {
    this.fetchAll()
  },

  async fetchAll() {
    try {
      const [list, stats] = await Promise.all([api.getRanking(10), api.getStats()])
      this.setData({ list, stats }, () => this.drawChart(list))
    } catch (err) {
      wx.showToast({ title: '加载失败，请确认后端已启动', icon: 'none' })
    }
  },

  // 自绘双系列柱状图：积分（橙）+ 点名次数（紫）
  drawChart(list) {
    if (!list || !list.length) return
    this.createSelectorQuery()
      .select('#chart')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0] || !res[0].node) return
        const canvas = res[0].node
        const width = res[0].width
        const height = res[0].height
        const dpr = wx.getWindowInfo().pixelRatio
        canvas.width = width * dpr
        canvas.height = height * dpr
        const ctx = canvas.getContext('2d')
        ctx.scale(dpr, dpr)

        const padL = 36
        const padR = 12
        const padT = 16
        const padB = 56
        const plotW = width - padL - padR
        const plotH = height - padT - padB
        const baseY = padT + plotH

        const scores = list.map((i) => i.score)
        const rolls = list.map((i) => i.roll_count)
        const maxRaw = Math.max(...scores, ...rolls, 1)
        const yMax = maxRaw <= 5 ? 5 : Math.ceil(maxRaw / 5) * 5
        const n = list.length
        const group = plotW / n
        const barW = Math.min(group * 0.3, 26)
        const start = Date.now()
        const duration = 600

        const draw = () => {
          const t = Math.min(1, (Date.now() - start) / duration)
          const ease = 1 - Math.pow(1 - t, 3)
          ctx.clearRect(0, 0, width, height)

          // 网格线与 y 轴刻度
          ctx.strokeStyle = '#f0ede8'
          ctx.fillStyle = '#b0a8a0'
          ctx.font = '10px sans-serif'
          ctx.textAlign = 'right'
          const ticks = 5
          for (let i = 0; i <= ticks; i++) {
            const yv = (yMax / ticks) * i
            const y = baseY - (plotH / ticks) * i
            ctx.beginPath()
            ctx.moveTo(padL, y)
            ctx.lineTo(width - padR, y)
            ctx.stroke()
            ctx.fillText(String(Math.round(yv * 10) / 10), padL - 6, y + 3)
          }
          // 基线
          ctx.strokeStyle = '#d9d2c8'
          ctx.beginPath()
          ctx.moveTo(padL, baseY)
          ctx.lineTo(width - padR, baseY)
          ctx.stroke()

          // 双系列柱
          for (let i = 0; i < n; i++) {
            const cx = padL + group * i + group / 2
            const sh = (scores[i] / yMax) * plotH * ease
            const rh = (rolls[i] / yMax) * plotH * ease
            ctx.fillStyle = '#FF9A3C'
            ctx.fillRect(cx - barW - 3, baseY - sh, barW, sh)
            ctx.fillStyle = '#7C4DFF'
            ctx.fillRect(cx + 3, baseY - rh, barW, rh)

            if (t >= 1) {
              ctx.fillStyle = '#8a8078'
              ctx.font = '9px sans-serif'
              ctx.textAlign = 'center'
              ctx.fillText(String(scores[i]), cx - barW / 2 - 3, baseY - sh - 4)
              ctx.fillText(String(rolls[i]), cx + barW / 2 + 3, baseY - rh - 4)
            }

            // x 轴姓名（旋转）
            ctx.save()
            ctx.fillStyle = '#8a8078'
            ctx.font = '10px sans-serif'
            ctx.textAlign = 'right'
            ctx.translate(cx, baseY + 12)
            ctx.rotate((-Math.PI * 55) / 180)
            const label =
              list[i].name.length > 4 ? list[i].name.slice(0, 4) + '…' : list[i].name
            ctx.fillText(label, 0, 0)
            ctx.restore()
          }

          if (t < 1) {
            canvas.requestAnimationFrame(draw)
          }
        }
        canvas.requestAnimationFrame(draw)
      })
  },

  // 导出积分详单 Excel
  exportExcel() {
    api
      .exportDetail()
      .catch((err) => wx.showToast({ title: err.message || '导出失败', icon: 'none' }))
  }
})