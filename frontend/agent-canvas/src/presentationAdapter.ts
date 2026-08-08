import type { PaletteTool } from './editorState'

export const CANVAS_PRESENTATION_VERSION = 'creative-v1' as const
export type CanvasPresentationMode = 'creative'|'legacy'
export type CreativeModality = 'text'|'image'|'video'|'audio'
export type PresentationTier = 'core'|'secondary'|'internal'

export type BlockPresentation = {
  modality: CreativeModality
  label: string
  icon: string
  tier: PresentationTier
  emptyTitle: string
  emptyHint: string
}

const modalityCopy:Record<CreativeModality,Omit<BlockPresentation,'modality'|'tier'>>={
  text:{label:'Văn bản',icon:'≡',emptyTitle:'Thêm văn bản',emptyHint:'Viết trực tiếp hoặc tạo bằng AI.'},
  image:{label:'Hình ảnh',icon:'▧',emptyTitle:'Thêm hình ảnh',emptyHint:'Kéo thả, tải lên hoặc tạo bằng AI.'},
  video:{label:'Video',icon:'▶',emptyTitle:'Thêm video',emptyHint:'Tải video hoặc tạo từ nội dung đã nối.'},
  audio:{label:'Âm thanh',icon:'♪',emptyTitle:'Thêm âm thanh',emptyHint:'Tải file hoặc tạo giọng nói bằng AI.'},
}

const coreTools:Record<CreativeModality,string>={
  text:'text.generate',image:'image.generate',video:'video.generate',audio:'audio.generate',
}

const explicitModalities:Record<string,CreativeModality>={
  'asset.image':'image','asset.images':'image','asset.video':'video','asset.audio':'audio',
  'text.generate':'text','text.script':'text','text.prompt_package':'text','story.storyboard':'text',
  'image.generate':'image','image.batch_generate':'image','image.thumbnail':'image','image.upscale':'image',
  'video.generate':'video','video.short_clips':'video','video.subtitle':'video','video.upscale':'video',
  'video.extract_frames':'image','video.social_import':'video','media.merge_image':'image',
  'media.merge_video':'video','audio.generate':'audio',
}

const actionLabels:Record<string,string>={
  'text.script':'Viết kịch bản','text.prompt_package':'Tạo gói prompt',
  'story.storyboard':'Tạo storyboard','image.batch_generate':'Tạo bộ ảnh',
  'image.thumbnail':'Tạo thumbnail','image.upscale':'Nâng cấp ảnh',
  'video.upscale':'Nâng cấp video','video.extract_frames':'Tách khung hình',
  'video.subtitle':'Tạo phụ đề','video.short_clips':'Tạo clip ngắn',
  'video.social_import':'Nhập video từ liên kết','media.merge_image':'Ghép ảnh',
  'media.merge_video':'Ghép video',
}

export function creativeModality(tool?:PaletteTool):CreativeModality|undefined{
  if(!tool)return undefined
  return explicitModalities[tool.name]
    ??(tool.name.startsWith('text.')?'text':tool.name.startsWith('image.')?'image':
      tool.name.startsWith('video.')?'video':tool.name.startsWith('audio.')?'audio':undefined)
}

export function blockPresentation(tool?:PaletteTool):BlockPresentation|undefined{
  const modality=creativeModality(tool)
  if(!tool||!modality)return undefined
  const tier:PresentationTier=tool.name.startsWith('asset.')?'internal':
    coreTools[modality]===tool.name?'core':'secondary'
  return {...modalityCopy[modality],modality,tier,
    label:tier==='core'||tier==='internal'?modalityCopy[modality].label:
      actionLabels[tool.name]??tool.label??modalityCopy[modality].label}
}

export function canonicalCreativeTools(palette:PaletteTool[]):PaletteTool[]{
  const visible=palette.filter(tool=>tool.customer_visible!==false)
  return (Object.keys(coreTools) as CreativeModality[]).flatMap(modality=>{
    const exact=visible.find(tool=>tool.name===coreTools[modality])
    const fallback=visible.find(tool=>creativeModality(tool)===modality&&!tool.name.startsWith('asset.'))
    return exact?[exact]:fallback?[fallback]:[]
  })
}

export function customerPaletteTools(palette:PaletteTool[],advanced=false):PaletteTool[]{
  if(!advanced)return canonicalCreativeTools(palette)
  return palette.filter(tool=>tool.customer_visible!==false&&
    blockPresentation(tool)?.tier!=='internal')
}

export function customerToolLabel(tool?:PaletteTool):string{
  return blockPresentation(tool)?.label??tool?.label??'Công cụ'
}

export function primaryOutputHandle(tool?:PaletteTool):string|undefined{
  if(!tool)return undefined
  const modality=creativeModality(tool)
  const wanted=modality==='text'?['text','script','prompt_package','storyboard']:
    modality==='image'?['image','image_key','image_keys','frames']:
    modality==='video'?['video','video_key','video_keys']:
    modality==='audio'?['audio','audio_key']:[]
  return wanted.find(name=>name in tool.returns)??Object.keys(tool.returns)[0]
}

function sourceKind(tool:PaletteTool|undefined,handle:string):CreativeModality|undefined{
  const kind=tool?.returns[handle]
  if(kind==='text')return 'text'
  if(kind==='image'||kind==='image[]')return 'image'
  if(kind==='video'||kind==='video[]')return 'video'
  if(kind==='audio'||kind==='audio[]')return 'audio'
  return creativeModality(tool)
}

export function connectionIntent(source:PaletteTool|undefined,sourceHandle:string,
                                 target:PaletteTool|undefined):string{
  const from=sourceKind(source,sourceHandle);const to=creativeModality(target)
  if(!from||!to)return `Nối tới ${customerToolLabel(target)}`
  if(to==='text')return from==='text'?'Viết tiếp hoặc biên tập':
    from==='image'?'Phân tích hình ảnh':from==='video'?'Phân tích video':'Phân tích âm thanh'
  if(to==='image')return from==='image'?'Chỉnh sửa hoặc biến thể ảnh':
    from==='video'?'Tách hoặc tạo ảnh từ video':'Tạo hình ảnh'
  if(to==='video')return from==='video'?'Chỉnh sửa hoặc xử lý video':
    from==='image'?'Tạo video từ hình ảnh':'Tạo video'
  return from==='audio'?'Xử lý âm thanh':'Tạo âm thanh'
}

export function destinationLabel(source:PaletteTool|undefined,sourceHandle:string,
                                 target:PaletteTool|undefined,targetLabel?:string):string{
  const label=(targetLabel||customerToolLabel(target)).trim()
  return `${connectionIntent(source,sourceHandle,target)} · ${label}`
}
