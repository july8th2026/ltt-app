async page => {
  const matrix = [];
  const quote = () => page.locator('#est').textContent();
  async function change(locator) {
    if (await locator.isChecked()) return;
    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/batch-quote') &&
        response.request().method() === 'POST'),
      locator.check(),
    ]);
  }
  for (const preset of ['fast', 'quality']) {
    for (const height of ['1080', '1440', '2160']) {
      await change(page.locator(`input[name=preset][value=${preset}]`));
      await change(page.locator(`input[name=target_height][value="${height}"]`));
      matrix.push({preset, height, quote: await quote()});
    }
  }
  await change(page.locator('#preview'));
  const preview = await quote();
  await change(page.locator('#stabilize'));
  const previewStabilize = await quote();
  await change(page.locator('#smooth_motion'));
  const smooth = {
    quote: await quote(),
    preserveFps: await page.locator('#preserve_fps').isChecked(),
    smooth: await page.locator('#smooth_motion').isChecked(),
  };
  await change(page.locator('#preserve_fps'));
  const fpsWins = {
    quote: await quote(),
    preserveFps: await page.locator('#preserve_fps').isChecked(),
    smooth: await page.locator('#smooth_motion').isChecked(),
  };
  await page.locator('select[name=codec]').selectOption('hevc');
  return {
    matrix,
    preview,
    previewStabilize,
    smooth,
    fpsWins,
    codec: await page.locator('select[name=codec]').inputValue(),
  };
}
