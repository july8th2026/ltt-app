async page => {
  await page.locator('input[type=file][accept="video/*"]').setInputFiles(
    'G:\\My Drive\\AI\\Tool AI\\Video seedacne\\video (10).mp4')
  await page.waitForTimeout(1700)
  await page.locator('input[type=file][accept*=".srt"]').setInputFiles(
    'D:\\LTTSTUDIOSAPP\\tests\\fixtures\\autosubvideo\\browser_sample.srt')
  await page.waitForTimeout(1300)
  await page.getByRole('button', {name:'Xin chào từ LTT Studios.'}).last().click()
  await page.getByRole('button', {name:'THE QUICK BROWN FOX TikTok Bold'}).click()
  await page.waitForTimeout(900)
  await page.getByRole('button', {name:'STYLE', exact:true}).click()
  await page.getByRole('slider', {name:'Cỡ chữ'}).fill('70')
  await page.getByRole('combobox', {name:'Karaoke'}).selectOption('word')
  await page.waitForTimeout(900)
  await page.getByRole('button', {name:'ANIMATION', exact:true}).click()
  await page.getByRole('button', {name:'Pop', exact:false}).click()
  await page.waitForTimeout(900)
}
