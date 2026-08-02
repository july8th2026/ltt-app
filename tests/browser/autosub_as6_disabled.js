async page => {
  await page.goto('http://127.0.0.1:8127/login')
  await page.getByRole('textbox', {name:'Tên đăng nhập'}).fill('autosub-ui@example.com')
  await page.getByRole('textbox', {name:'Mật khẩu'}).fill('Browser-test-123')
  await page.getByRole('button', {name:'Đăng nhập'}).click()
  await page.goto('http://127.0.0.1:8127/autosubvideo')
  await page.setViewportSize({width:1440,height:1000})
  await page.locator('input[type=file][accept="video/*"]').setInputFiles(
    'G:\\My Drive\\AI\\Tool AI\\Video seedacne\\video (10).mp4')
  await page.waitForTimeout(1500)
  await page.locator('input[type=file][accept*=".srt"]').setInputFiles(
    'D:\\LTTSTUDIOSAPP\\tests\\fixtures\\autosubvideo\\browser_sample.srt')
  await page.waitForTimeout(1000)
}
