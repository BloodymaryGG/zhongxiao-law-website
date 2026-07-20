/**
 * 在线咨询表单提交处理
 *
 * Cloudflare Pages Function
 * 接收表单 POST 请求，通过邮件 API 转发到律所邮箱
 *
 * 使用方式：
 * 1. 在 resend.com 注册免费账号（100封/天，够用）
 * 2. 创建 API Key
 * 3. 在 Cloudflare Pages 的项目的「环境变量」中添加：
 *    - RESEND_API_KEY = re_xxxxx
 *    - TO_EMAIL = 534818861@qq.com
 *    - FROM_EMAIL = 咨询表单 <consult@你的域名.com>
 *
 * 注：如果不配置环境变量，表单会正常返回成功但不会发邮件（不会报错让客户看到）
 */

export async function onRequest(context) {
  const { request, env } = context;
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  // CORS 预检
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers });
  }

  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers,
    });
  }

  try {
    const formData = await request.formData();
    const name = formData.get('name')?.trim() || '';
    const phone = formData.get('phone')?.trim() || '';
    const email = formData.get('email')?.trim() || '(未填写)';
    const message = formData.get('message')?.trim() || '';

    // 基本校验
    if (!name || !phone || !message) {
      return new Response(
        JSON.stringify({ success: false, error: '请填写姓名、电话和咨询内容' }),
        { status: 400, headers }
      );
    }

    // 如果配置了邮件 API，发送通知
    if (env.RESEND_API_KEY && env.TO_EMAIL) {
      const fromEmail = env.FROM_EMAIL || '咨询表单 <onboarding@resend.dev>';
      const emailRes = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.RESEND_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: fromEmail,
          to: env.TO_EMAIL,
          subject: `📩 新法律咨询 - ${name}`,
          html: `
            <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 600px; margin: 0 auto;">
              <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 24px; text-align: center;">
                <h1 style="color: #fff; margin: 0; font-size: 20px; letter-spacing: 2px;">北京中晓律师事务所</h1>
                <p style="color: rgba(255,255,255,0.6); margin: 8px 0 0; font-size: 13px;">新法律咨询通知</p>
              </div>
              <div style="padding: 24px; background: #f9f9f9;">
                <table style="width: 100%; border-collapse: collapse;">
                  <tr>
                    <td style="padding: 10px 0; color: #666; width: 80px; font-size: 14px;">👤 姓名</td>
                    <td style="padding: 10px 0; font-size: 14px; font-weight: 600;">${escapeHtml(name)}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; color: #666; width: 80px; font-size: 14px; border-top: 1px solid #eee;">📞 电话</td>
                    <td style="padding: 10px 0; font-size: 14px; border-top: 1px solid #eee;">
                      <a href="tel:${escapeHtml(phone)}" style="color: #1a73e8; text-decoration: none;">${escapeHtml(phone)}</a>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; color: #666; width: 80px; font-size: 14px; border-top: 1px solid #eee;">📧 邮箱</td>
                    <td style="padding: 10px 0; font-size: 14px; border-top: 1px solid #eee;">
                      <a href="mailto:${escapeHtml(email)}" style="color: #1a73e8; text-decoration: none;">${escapeHtml(email)}</a>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; color: #666; width: 80px; font-size: 14px; vertical-align: top; border-top: 1px solid #eee;">💬 内容</td>
                    <td style="padding: 10px 0; font-size: 14px; border-top: 1px solid #eee;">
                      <div style="background: #fff; padding: 16px; border-radius: 6px; border: 1px solid #e0e0e0; line-height: 1.6;">${escapeHtml(message)}</div>
                    </td>
                  </tr>
                </table>
                <p style="margin-top: 20px; font-size: 12px; color: #999; text-align: center;">
                  收到时间：${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                </p>
              </div>
              <div style="padding: 16px; text-align: center; background: #fff; border-top: 1px solid #eee;">
                <p style="margin: 0; font-size: 11px; color: #bbb;">北京中晓律师事务所 · 以法立心 · 向晓而行</p>
              </div>
            </div>
          `,
        }),
      });

      if (!emailRes.ok) {
        const errText = await emailRes.text();
        console.error('Resend API error:', errText);
        // 不让客户看到后端错误，仍返回成功
      }
    }

    return new Response(
      JSON.stringify({ success: true }),
      { status: 200, headers }
    );
  } catch (err) {
    console.error('Form submission error:', err);
    return new Response(
      JSON.stringify({ success: true }), // 容错，不让客户看到 500
      { status: 200, headers }
    );
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
