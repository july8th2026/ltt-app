async page => {
  const source = 'C:/Users/Thang Tuong/Desktop/AppLttStudio_11082026/UpscaleVideo/VideoTest.mp4';
  await page.locator('#batch_mode').check();
  await page.locator('#vfile').setInputFiles([source, source]);
  await page.waitForFunction(() =>
    document.querySelectorAll('#batch-files > span').length === 2);
  await page.waitForFunction(() => /2 video/.test(
    document.querySelector('#est').textContent));
  const before = {
    files: await page.locator('#batch-files > span').count(),
    quote: await page.locator('#est').textContent(),
    credit: await page.locator('a[href="/nap"]').last().textContent(),
  };
  await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/upscalevideo/batch')),
    page.locator('#submitbtn').click(),
  ]);
  await page.waitForFunction(() => document.querySelectorAll('.up-job').length >= 5);
  return {
    before,
    jobs: await page.locator('.up-job').count(),
    topStates: await page.locator('.up-job .up-state').evaluateAll(items =>
      items.slice(0, 2).map(item => item.textContent.trim())),
    credit: await page.locator('a[href="/nap"]').last().textContent(),
  };
}
