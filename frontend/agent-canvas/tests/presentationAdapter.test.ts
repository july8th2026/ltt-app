import {describe,expect,it} from 'vitest'
import type {PaletteTool} from '../src/editorState'
import {blockPresentation,CANVAS_PRESENTATION_VERSION,canonicalCreativeTools,
  connectionIntent,customerPaletteTools,customerToolLabel,destinationLabel,
  primaryOutputHandle} from '../src/presentationAdapter'

const make=(name:string,returns:Record<string,string>={text:'text'}):PaletteTool=>({name,
  label:name,description:'internal description',app_slug:'x',app_name:'X',requires:[],verifiable:[],
  primary:false,category:name.startsWith('asset.')?'input':'advanced',params_schema:{},returns})

const publicNames=['text.generate','text.script','text.prompt_package','story.storyboard',
  'image.generate','image.batch_generate','image.thumbnail','image.upscale','video.generate',
  'video.short_clips','video.subtitle','video.upscale','video.extract_frames','video.social_import',
  'media.merge_image','media.merge_video','audio.generate','asset.image','asset.images','asset.video','asset.audio']

describe('creative presentation adapter',()=>{
  it('covers every public ToolSpec without changing the document/runtime contract',()=>{
    expect(CANVAS_PRESENTATION_VERSION).toBe('creative-v1')
    for(const name of publicNames)expect(blockPresentation(make(name)),name).toBeDefined()
    expect(blockPresentation(make('asset.image'))?.tier).toBe('internal')
    expect(customerToolLabel(make('text.generate'))).toBe('Văn bản')
    expect(customerToolLabel(make('video.subtitle'))).toBe('Tạo phụ đề')
  })

  it('shows exactly four canonical blocks and hides asset implementations',()=>{
    const palette=[make('asset.image',{image_key:'image'}),make('video.generate',{video_key:'video'}),
      make('audio.generate',{audio_key:'audio'}),make('image.generate',{image_keys:'image[]'}),
      make('text.generate'),make('image.upscale',{image_key:'image'})]
    expect(canonicalCreativeTools(palette).map(tool=>tool.name)).toEqual([
      'text.generate','image.generate','video.generate','audio.generate'])
    expect(customerPaletteTools(palette).map(tool=>tool.name)).toEqual([
      'text.generate','image.generate','video.generate','audio.generate'])
    expect(customerPaletteTools(palette,true).map(tool=>tool.name)).not.toContain('asset.image')
    expect(primaryOutputHandle(palette[3])).toBe('image_keys')
  })

  it('keeps soft-retired tools resolvable but removes them from customer menus',()=>{
    const retired={...make('text.script'),customer_visible:false}
    const palette=[retired,make('text.generate'),make('image.generate',{image_keys:'image[]'})]
    expect(palette.find(tool=>tool.name==='text.script')).toBe(retired)
    expect(customerPaletteTools(palette,true).map(tool=>tool.name)).not.toContain('text.script')
  })

  it('uses human intent and a unique destination label instead of field names',()=>{
    const text=make('text.generate',{text:'text'});const image=make('image.generate',{image_keys:'image[]'})
    expect(connectionIntent(text,'text',image)).toBe('Tạo hình ảnh')
    expect(connectionIntent(image,'image_keys',text)).toBe('Phân tích hình ảnh')
    expect(destinationLabel(text,'text',image,'Ảnh sản phẩm')).toBe('Tạo hình ảnh · Ảnh sản phẩm')
    expect(destinationLabel(text,'text',image,'Ảnh sản phẩm')).not.toContain('prompt')
  })
})
