import { createRouter, createWebHistory } from 'vue-router'
// 引入用户权限相关函数
import { isAuditor, fetchCurrentUser, currentUser } from '../stores/user'

// 1Panel 方案：根路由不用 redirect（避免加载前触发额外导航导致循环），
// 改用 path: '' 作为默认子路由，让导航守卫统一处理
const routes = [
  {path: '/', name: 'Layout', component: () => import('../views/Layout.vue'),
    children: [
      {path: '', name: 'Home', component: () => import('../views/Home.vue'), meta: { title: '仪表盘' }},
      {path: 'home', name: 'HomeAlias', component: () => import('../views/Home.vue'), meta: { title: '仪表盘' }},
      {path: 'file', name: 'File', component: () => import('../views/file/File.vue'), meta: { title: '文件管理', noAuditor: true }},
      {path: 'host', name: 'Host', component: () => import('../views/host/Base.vue'),redirect: '/host/terminal', meta: { title: 'Ansible', noAuditor: true },
        children: [
          {path: 'terminal', name: 'Terminal', component: () => import('../views/host/Terminal.vue'), meta: { title: '终端' }} ,
          {path: 'hosts', name: 'Hosts', component: () => import('../views/host/Hosts.vue'), meta: { title: '主机管理' }} ,
          {path: 'scripts', name: 'Scripts', component: () => import('../views/host/Scripts.vue'), meta: { title: '脚本库' }} ,
          {path: 'crontab', name: 'Crontab', component: () => import('../views/host/Crontab.vue'), meta: { title: '定时任务' }} ,
          {path: 'filetransfer', name: 'FileTransfer', component: () => import('../views/host/FileTransfer.vue'), meta: { title: '文件传输' }} ,
        ]
      },
      {path: 'logs', name: 'Logs', component: () => import('../views/logs/Base.vue'),redirect: '/logs/systemlog', meta: { title: '日志审计' },
        children: [
          {path: 'systemlog', name: 'SystemLog', component: () => import('../views/logs/SystemLogs.vue'), meta: { title: '系统日志' }} ,
          {path: 'access', name: 'Access', component: () => import('../views/logs/AccessLog.vue'), meta: { title: '访问日志' }} ,
          {path: 'loginLogs', name: 'LoginLogs', component: () => import('../views/logs/LoginLog.vue'), meta: { title: '登录日志' }} ,
        ]
      },
      {path: 'container', name: 'Container', component: () => import('../views/container/Base.vue'),redirect: '/container/overview', meta: { title: '容器管理', noAuditor: true },
        children: [
          {path: 'overview', name: 'Overview', component: () => import('../views/container/Overview.vue'), meta: { title: '基本概况' }} ,
          {path: 'containers', name: 'Containers', component: () => import('../views/container/Containers.vue'), meta: { title: '容器列表' }} ,
          {path: 'images', name: 'Images', component: () => import('../views/container/Images.vue'), meta: { title: '镜像管理' }} ,
          {path: 'networks', name: 'Networks', component: () => import('../views/container/Networks.vue'), meta: { title: '网络管理' }} ,
          {path: 'volumes', name: 'Volumes', component: () => import('../views/container/Volumes.vue'), meta: { title: '卷管理' }} ,
          {path: 'compose', name: 'Compose', component: () => import('../views/container/Compose.vue'), meta: { title: '容器编排' }} ,
          {path: 'containerHost', name: 'ContainerHost', component: () => import('../views/container/ContainerHost.vue'), meta: { title: '容器宿主机' }} ,
        ]
      },
       {path: 'security', name: 'Security', component: () => import('../views/security/Base.vue'), redirect: '/security/firewall', meta: { title: '安全管理', noAuditor: true },
         children: [
           {path: 'firewall', name: 'Firewall', component: () => import('../views/security/Firewall.vue'), meta: { title: '防火墙' }},
           {path: 'ssh-manager', name: 'SSH', component: () => import('../views/security/SSH.vue'), meta: { title: 'SSH管理' }} ,
           {path: 'process', name: 'Process', component: () => import('../views/security/Process.vue'), meta: { title: '进程管理' }} ,
           {path: 'network-list', name: 'NetworkList', component: () => import('../views/security/NetworkList.vue'), meta: { title: '网络管理' }} ,
         ]
       },
      {path: 'waf', name: 'Waf', component: () => import('../views/waf/Base.vue'),redirect: '/waf/basic', meta: { title: 'WAF', noAuditor: true },
        children: [
          {path: 'basic', name: 'Basic', component: () => import('../views/waf/Basic.vue'), meta: { title: '概况' }} ,
          {path: 'sites', name: 'Sites', component: () => import('../views/waf/Sites.vue'), meta: { title: '站点' }} ,
          {path: 'blackwhite', name: 'BlackWhite', component: () => import('../views/waf/BlackWhite.vue'), meta: { title: '黑白名单' }} ,
          {path: 'ssl', name: 'SSL', component: () => import('../views/waf/SSL.vue'), meta: { title: 'SSL证书' }} ,
          {path: 'rules', name: 'Rules', component: () => import('../views/waf/Rules.vue'), meta: { title: '规则' }} ,
          {path: 'log', name: 'Log', component: () => import('../views/waf/Log.vue'), meta: { title: '日志' }} ,
          {path: 'global', name: 'GlobalSetting', component: () => import('../views/waf/GlobalSetting.vue'), meta: { title: '全局设置' }} ,
        ]
      },
      {path: 'settings', name: 'Settings', component: () => import('../views/settings/Base.vue'),redirect: '/settings/system', meta: { title: '系统设置' },
        children: [
          {path: 'system', name: 'System', component: () => import('../views/settings/System.vue'), meta: { title: '系统' }} ,
          {path: 'user', name: 'User', component: () => import('../views/settings/User.vue'), meta: { title: '用户' }},
        ]
      },
      {path: 'database', name: 'Database', component: () => import('../views/database/Base.vue'),redirect: '/database/mysql',  meta: { title: '数据库管理' },
        children: [
          {path: 'sqlite', name: 'Sqlite', component: () => import('../views/database/Sqlite.vue'), meta: { title: 'SQLite' }} ,
          {path: 'sqlite/:id/manage', name: 'SqliteManager', component: () => import('../views/database/SqliteManager.vue'), meta: { title: '表管理' }} ,
          {path: 'mysql', name: 'Mysql', component: () => import('../views/database/Mysql.vue'), meta: { title: 'MySQL' }} ,
          {path: 'mysql/:id/manage', name: 'MysqlManager', component: () => import('../views/database/MysqlManager.vue'), meta: { title: 'MySQL 管理' }} ,
          {path: 'postgresql', name: 'Postgresql', component: () => import('../views/database/Postgresql.vue'), meta: { title: 'PostgreSQL' }} ,
          {path: 'postgresql/:id/manage', name: 'PostgresqlManager', component: () => import('../views/database/PostgresqlManager.vue'), meta: { title: 'PostgreSQL 管理' }} ,
        ]
      },
    ]
  },
  {path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录' }},
  {path: '/:code?', name: 'Entrance', component: () => import('../views/Login.vue'), meta: { title: '登录' }},
  {path: '/bigScreen', name: 'BigScreen', component: () => import('../views/BigScreen.vue'), meta: { title: '大屏' }},
  {path: '/:pathMatch(.*)*', redirect: '/home'},
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加导航守卫
router.beforeEach(async (to, from, next) => {
  // 1. 入口路由（/:code?）— 直接渲染 Login.vue，与 1Panel 完全一致
  if (to.name === 'Entrance') {
    if (to.params.code) {
      localStorage.setItem('security_entrance', to.params.code)
    }
    next()
    return
  }

  // 2. 登录页 — 直接放行
  if (to.path === '/login') {
    next()
    return
  }

  const token = localStorage.getItem('access_token')

  // 3. 没有 token → 跳转登录
  if (!token) {
    const entrance = localStorage.getItem('security_entrance')
    next(entrance ? '/' + entrance : '/login')
    return
  }

  // 4. 有 token 但未加载用户信息 → 获取
  if (!currentUser.value) {
    try {
      await fetchCurrentUser()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      const entrance = localStorage.getItem('security_entrance')
      next(entrance ? '/' + entrance : '/login')
      return
    }
  }

  // 5. 权限检查：auditor 不能访问 noAuditor 路由
  try {
    if (isAuditor()) {
      const hasNoAuditor = to.matched.some(record => record.meta.noAuditor)
      if (hasNoAuditor) {
        next('/home')
        return
      }
    }
  } catch (error) {
    console.error('权限检查失败:', error)
  }

  next()
})

export default router
