import { createRouter, createWebHistory } from 'vue-router'
// 引入加载状态管理
import { startGlobalLoading, endGlobalLoading } from '../utils/loading'
// 引入用户权限相关函数
import { isAuditor, fetchCurrentUser, currentUser } from '../stores/user'

const routes = [
  {path: '/', name: 'Layout', component: () => import('../views/Layout.vue'), redirect: '/home', meta: { title: '主界面' },
    children: [
      {path: 'home', name: 'Home', component: () => import('../views/Home.vue'), meta: { title: '仪表盘' }},
      {path: 'file', name: 'File', component: () => import('../views/file/File.vue'), meta: { title: '文件管理', noAuditor: true }},
      {path: 'host', name: 'Host', component: () => import('../views/host/Base.vue'),redirect: '/host/terminal', meta: { title: 'Ansible', noAuditor: true },
        children: [
          {path: 'terminal', name: 'Terminal', component: () => import('../views/host/Terminal.vue'), meta: { title: '终端' }} ,
          {path: 'hosts', name: 'Hosts', component: () => import('../views/host/Hosts.vue'), meta: { title: '主机管理' }} ,
          {path: 'scripts', name: 'Scripts', component: () => import('../views/host/Scripts.vue'), meta: { title: '脚本库' }} ,
          {path: 'crontab', name: 'Crontab', component: () => import('../views/host/Crontab.vue'), meta: { title: '定时任务' }} ,
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
  {path: '/bigScreen', name: 'BigScreen', component: () => import('../views/BigScreen.vue'), meta: { title: '大屏' }},
  {path: '/:pathMatch(.*)*', redirect: '/home'},
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加导航守卫
router.beforeEach(async (to, from, next) => {
  // 判断是否是父级路由切换
  const isParentRouteChange = getParentPath(to.path) !== getParentPath(from.path);
  
  // 只有在父级路由切换时才显示加载动画
  if (isParentRouteChange) {
    startGlobalLoading();
  }

  const token = localStorage.getItem('access_token')

  // 如果访问的是登录页，直接放行
  if (to.path === '/login') {
    next()
    return
  }

  // 如果没有token且访问的不是登录页，则跳转到登录页
  if (!token && to.path !== '/login') {
    // 如果是父级路由切换，立即结束加载动画，因为要重定向
    if (isParentRouteChange) {
      endGlobalLoading();
    }
    next('/login')
    return
  }

  // 确保用户信息已加载
  if (!currentUser.value) {
    console.log('权限检查: 用户信息未加载，正在获取...');
    try {
      await fetchCurrentUser();
      console.log('权限检查: 用户信息加载完成:', currentUser.value);
    } catch (error) {
      console.error('获取用户信息失败:', error);
      // 如果是父级路由切换，结束加载动画
      if (isParentRouteChange) {
        endGlobalLoading();
      }
      // 重定向到登录页
      next('/login');
      return;
    }
  }

  // 权限检查：如果用户是auditor且尝试访问标记为noAuditor的路由，则重定向到首页
  try {
    // 检查是否是auditor用户
    const auditorCheck = isAuditor();
    // console.log('权限检查: 当前用户角色审计检查结果:', auditorCheck);
    // console.log('权限检查: 访问路径:', to.path);
    // console.log('权限检查: 用户角色:', currentUser.value?.role || '未知');
    // console.log('权限检查: 路由匹配链:', to.matched.map(record => `${record.path}: ${record.meta.noAuditor ? 'noAuditor' : 'allowed'}`));
    
    if (auditorCheck) {
      // 检查整个路由匹配链是否包含noAuditor标记
      // 包括当前路由和所有父级路由
      const hasNoAuditor = to.matched.some(record => record.meta.noAuditor);
      console.log('权限检查: 检测到noAuditor标记:', hasNoAuditor);
      
      if (hasNoAuditor) {
        // 如果是父级路由切换，立即结束加载动画
        if (isParentRouteChange) {
          endGlobalLoading();
        }
        // 重定向到首页
        console.log('权限检查: 审计员用户尝试访问受限页面，重定向到首页');
        next('/home');
        return;
      } else {
        console.log('权限检查: 审计员用户访问允许的页面');
      }
    } else {
      console.log('权限检查: 非审计员用户，正常访问');
    }
  } catch (error) {
    console.error('权限检查失败:', error);
  }

  // 其他情况直接放行
  next()
})

// 路由加载完成后的回调
router.afterEach((to, from) => {
  // 判断是否是父级路由切换
  const isParentRouteChange = getParentPath(to.path) !== getParentPath(from.path);
  
  // 只有在父级路由切换时才结束加载动画
  if (isParentRouteChange) {
    setTimeout(() => {
      endGlobalLoading();
    }, 1000);
  }
})

// 获取路由路径的父级部分
function getParentPath(path) {
  // 特殊处理：登录页作为独立的父级路由
  if (path === '/login') return 'login';
  
  // 对于根路径，返回空字符串
  if (path === '/') return '';
  
  // 分割路径并取前两部分（第一个是空字符串，第二个是父级路由）
  const parts = path.split('/');
  if (parts.length > 1) {
    return parts[1] || '';
  }
  return '';
}

export default router