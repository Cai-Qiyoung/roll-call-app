// 后端接口地址（开发阶段填本地，上线后换成 HTTPS 域名）
const BASE_URL = 'http://127.0.0.1:8000'

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const msg = res.data && (res.data.detail || res.data.message)
          reject(new Error(msg || `请求失败(${res.statusCode})`))
        }
      },
      fail() {
        reject(new Error('无法连接后端，请确认服务已启动'))
      }
    })
  })
}

function uploadFile(path, filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}${path}`,
      filePath,
      name: 'file',
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(JSON.parse(res.data))
        } else {
          reject(new Error('导入失败'))
        }
      },
      fail() {
        reject(new Error('无法连接后端'))
      }
    })
  })
}

// 下载后端生成的 xlsx 并用系统预览打开（可分享/转发给老师）
function downloadAndOpen(path) {
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '生成中' })
    wx.downloadFile({
      url: `${BASE_URL}${path}`,
      success(res) {
        wx.hideLoading()
        if (res.statusCode !== 200) return reject(new Error('下载失败'))
        wx.openDocument({
          filePath: res.tempFilePath,
          fileType: 'xlsx',
          showMenu: true,
          success: resolve,
          fail: () => reject(new Error('打开文件失败'))
        })
      },
      fail() {
        wx.hideLoading()
        reject(new Error('下载失败'))
      }
    })
  })
}

module.exports = {
  // 登录（保留接口，后续拿到 AppID 可启用）
  login: (code) => request('/auth/login', { method: 'POST', data: { code } }),

  // 学生名单
  getStudents: () => request('/students'),
  importFile: (filePath) => uploadFile('/students/import', filePath),
  downloadTemplate: () => downloadAndOpen('/students/template'),
  deleteStudent: (no) => request(`/students/${no}`, { method: 'DELETE' }),
  clearStudents: () => request('/students', { method: 'DELETE' }),

  // 点名
  randomRoll: (thursday) =>
    request(`/rollcall/random?thursday=${thursday ? 1 : 0}`, { method: 'POST' }),
  sequenceRoll: () => request('/rollcall/sequence', { method: 'POST' }),
  confirmRoll: (data) => request('/rollcall/confirm', { method: 'POST', data }),
  scoreAnswer: (data) => request('/rollcall/score', { method: 'POST', data }),
  transfer: (from, to) =>
    request('/rollcall/transfer', {
      method: 'POST',
      data: { from_student_no: from, to_student_no: to }
    }),

  // 排名与导出
  getRanking: (n = 10) => request(`/ranking/top?n=${n}`),
  getStats: () => request('/ranking/stats'),
  exportDetail: () => downloadAndOpen('/ranking/export'),

  // 积分商店
  getShopItems: () => request('/shop/items'),
  getWallet: (no) => request(`/shop/${no}`),
  exchange: (no, code) =>
    request('/shop/exchange', {
      method: 'POST',
      data: { student_no: no, item_code: code }
    })
}