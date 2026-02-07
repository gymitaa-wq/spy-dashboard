"""
Google OAuth 认证模块
提供 Streamlit 应用的 Google 登录功能
"""

import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import Optional, Dict, Any


class GoogleAuthenticator:
    """Google OAuth 认证管理器"""

    # OAuth 2.0 scopes
    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]

    def __init__(self):
        """初始化认证器"""
        self.client_id = st.secrets.get("google_oauth", {}).get("client_id", "")
        self.client_secret = st.secrets.get("google_oauth", {}).get("client_secret", "")
        self.redirect_uri = st.secrets.get("google_oauth", {}).get("redirect_uri", "http://localhost:8501")
        self.allowed_domains = st.secrets.get("google_oauth", {}).get("allowed_domains", [])
        self.allowed_emails = st.secrets.get("google_oauth", {}).get("allowed_emails", [])

        # 检查配置
        if not self.client_id or not self.client_secret:
            st.error("⚠️ Google OAuth 配置未完成，请在 .streamlit/secrets.toml 中配置")
            st.info("请参考 .streamlit/secrets.toml.example 文件")
            st.stop()

    def create_flow(self) -> Flow:
        """创建 OAuth Flow"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        return flow

    def get_authorization_url(self) -> str:
        """获取授权 URL"""
        flow = self.create_flow()
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # 保存 state 到 session
        st.session_state['oauth_state'] = state

        return auth_url

    def fetch_token(self, authorization_response: str) -> Optional[Credentials]:
        """使用授权码获取 token"""
        try:
            flow = self.create_flow()
            flow.fetch_token(authorization_response=authorization_response)
            return flow.credentials
        except Exception as e:
            st.error(f"获取 token 失败: {str(e)}")
            return None

    def get_user_info(self, credentials: Credentials) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            st.error(f"获取用户信息失败: {str(e)}")
            return None

    def is_user_allowed(self, user_info: Dict[str, Any]) -> bool:
        """检查用户是否有访问权限"""
        email = user_info.get('email', '')

        # 如果没有设置任何限制，允许所有用户
        if not self.allowed_domains and not self.allowed_emails:
            return True

        # 检查邮箱是否在允许列表中
        if self.allowed_emails and email in self.allowed_emails:
            return True

        # 检查域名是否在允许列表中
        if self.allowed_domains:
            domain = email.split('@')[-1] if '@' in email else ''
            if domain in self.allowed_domains:
                return True

        return False

    def logout(self):
        """登出"""
        keys_to_clear = ['authenticated', 'user_info', 'credentials', 'oauth_state']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def require_authentication():
    """
    装饰器函数：要求用户必须通过 Google 登录才能访问
    在主应用开始时调用此函数
    """
    authenticator = GoogleAuthenticator()

    # 初始化 session state
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    # 如果已经认证，直接返回
    if st.session_state['authenticated']:
        return

    # 显示登录页面
    st.title("🔐 SPY Put Selling Dashboard")
    st.markdown("### 请使用 Google 账号登录")

    # 处理 OAuth 回调
    query_params = st.query_params

    if 'code' in query_params:
        # 用户已授权，获取 token
        authorization_response = st.query_params.to_dict()
        full_url = f"{authenticator.redirect_uri}?code={authorization_response['code']}"

        if 'state' in authorization_response:
            full_url += f"&state={authorization_response['state']}"

        credentials = authenticator.fetch_token(full_url)

        if credentials:
            # 获取用户信息
            user_info = authenticator.get_user_info(credentials)

            if user_info:
                # 检查用户权限
                if authenticator.is_user_allowed(user_info):
                    # 保存认证信息
                    st.session_state['authenticated'] = True
                    st.session_state['user_info'] = user_info
                    st.session_state['credentials'] = credentials

                    # 清除 URL 参数
                    st.query_params.clear()

                    st.success(f"✅ 登录成功！欢迎 {user_info.get('name', 'User')}")
                    st.rerun()
                else:
                    st.error("❌ 您没有访问权限")
                    st.info(f"您的邮箱: {user_info.get('email', 'Unknown')}")
                    if st.button("返回"):
                        st.query_params.clear()
                        st.rerun()
                    st.stop()

    # 显示登录按钮
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.info("📊 此应用提供 SPY、QQQ、TSLA、IBIT 等标的的期权数据分析")

        if st.button("🔑 使用 Google 账号登录", type="primary", use_container_width=True):
            auth_url = authenticator.get_authorization_url()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
            st.markdown(f"[点击此处登录]({auth_url})")

    st.markdown("---")
    st.caption("🔒 我们使用 Google OAuth 2.0 进行安全认证，不会存储您的密码")

    st.stop()


def show_user_info():
    """在侧边栏显示用户信息和登出按钮"""
    if st.session_state.get('authenticated', False):
        user_info = st.session_state.get('user_info', {})

        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 用户信息")

            # 显示头像
            if 'picture' in user_info:
                st.image(user_info['picture'], width=80)

            st.write(f"**{user_info.get('name', 'User')}**")
            st.caption(user_info.get('email', ''))

            if st.button("🚪 登出", use_container_width=True):
                authenticator = GoogleAuthenticator()
                authenticator.logout()
