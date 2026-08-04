import type { PaletteTool } from './editorState'

export type NodeModality = 'text'|'image'|'video'|'audio'|'batch'|'transform'|'input'|'tool'

export const fieldLabels: Record<string,string> = {
  prompt:'Mô tả', topic:'Chủ đề', model:'Model', aspect_ratio:'Tỷ lệ',
  resolution:'Độ phân giải', duration:'Thời lượng', count:'Số lượng',
  voice:'Giọng đọc', language:'Ngôn ngữ', url:'Liên kết', source_url:'Liên kết',
  target_height:'Độ phân giải đích', preset:'Chất lượng', scale:'Mức phóng đại',
  interval:'Khoảng cách khung hình', fps:'Khung hình/giây', layout:'Bố cục',
  direction:'Hướng ghép', generate_audio:'Tạo âm thanh', preserve_audio:'Giữ âm thanh',
  preserve_fps:'Giữ tốc độ khung hình', images:'Ảnh đầu vào', videos:'Video đầu vào',
  image_key:'Ảnh đầu vào', video_key:'Video đầu vào', audio_key:'Âm thanh đầu vào',
  image_keys:'Bộ ảnh đầu vào', video_keys:'Bộ video đầu vào', source_text:'Văn bản tham chiếu',
  text:'Nội dung',
  confirm_rights:'Tôi xác nhận có quyền sử dụng video',
}

export function nodeModality(tool?: PaletteTool): NodeModality {
  const name=tool?.name??''
  if(name==='asset.images')return 'batch'
  if(name.includes('batch'))return 'batch'
  if(tool?.category==='transform'||/upscale|extract|merge/.test(name))return 'transform'
  if(name==='asset.image')return 'image'
  if(name==='asset.video')return 'video'
  if(name==='asset.audio')return 'audio'
  if(name.startsWith('asset.')||name.includes('social_import'))return 'input'
  if(name.startsWith('text.'))return 'text'
  if(name.startsWith('image.'))return 'image'
  if(name.startsWith('video.'))return 'video'
  if(name.startsWith('audio.'))return 'audio'
  return 'tool'
}

export function nodeTitle(tool?:PaletteTool){
  if(tool?.name==='asset.image')return 'Hình ảnh'
  if(tool?.name==='asset.images')return 'Bộ ảnh'
  if(tool?.name==='asset.video')return 'Video'
  if(tool?.name==='asset.audio')return 'Âm thanh'
  return tool?.label||tool?.name||'Công cụ không tồn tại'
}

export function mediaKind(tool?:PaletteTool):'image'|'video'|'audio'|undefined {
  const name=tool?.name??''
  if(name.startsWith('image.')||name==='asset.image'||name==='asset.images')return 'image'
  if(name.startsWith('video.')||name==='asset.video'||name.includes('video'))return 'video'
  if(name.startsWith('audio.')||name==='asset.audio')return 'audio'
  return undefined
}

export function fieldLabel(name:string){
  return fieldLabels[name]??name.replace(/_+/g,' ').replace(/^./,letter=>letter.toLocaleUpperCase('vi'))
}

export function outputLabel(name:string,kind:string){
  if(kind==='image'||kind==='image[]')return kind.endsWith('[]')?'Bộ ảnh':'Hình ảnh'
  if(kind==='video'||kind==='video[]')return kind.endsWith('[]')?'Bộ video':'Video'
  if(kind==='audio')return 'Âm thanh'
  if(kind==='text')return 'Nội dung'
  if(kind==='json')return 'Dữ liệu'
  return fieldLabel(name)
}

const priorities=['prompt','topic','text','url','source_url','model','aspect_ratio','resolution',
  'duration','count','voice','language','target_height','preset','scale','interval','fps',
  'layout','direction','generate_audio','preserve_audio','preserve_fps']

export function primaryFields(tool:PaletteTool,params:Record<string,unknown>){
  if(tool.name.startsWith('asset.'))return []
  const schema=Object.entries(tool.schema_variants??{}).reduce((current,[field,variants])=>
    variants[String(params[field])]??current,tool.params_schema)
  return Object.entries(schema).filter(([name,rule])=>
    !['image','video','audio','image[]','video[]'].includes(rule.type)&&
    (priorities.includes(name)||rule.required||rule.type==='model_ref'||rule.values?.length))
    .sort(([a],[b])=>(priorities.indexOf(a)<0?999:priorities.indexOf(a))-(priorities.indexOf(b)<0?999:priorities.indexOf(b)))
    .slice(0,6)
}

export function emptyMessage(tool?:PaletteTool){
  if(tool?.name==='video.social_import')return {title:'Thêm Social Video',
    hint:'Dán liên kết TikTok, YouTube Shorts hoặc Reels mà bạn có quyền sử dụng.'}
  const mode=nodeModality(tool)
  if(mode==='image')return {title:'Thêm một hình ảnh',hint:'Kéo thả, tải lên hoặc tạo bằng AI.'}
  if(mode==='video')return {title:'Thêm một video',hint:'Tải video hoặc tạo từ mô tả và nội dung đã nối.'}
  if(mode==='audio')return {title:'Thêm âm thanh',hint:'Tải file hoặc tạo giọng nói, nhạc và hiệu ứng.'}
  if(mode==='text')return {title:'Thêm nội dung',hint:'Viết yêu cầu hoặc tạo nội dung bằng AI.'}
  if(mode==='batch')return {title:'Thêm bộ ảnh',hint:'Tải nhiều ảnh hoặc tạo một batch có kiểm soát.'}
  if(mode==='transform')return {title:'Kết nối nội dung đầu vào',hint:'Nối output tương thích rồi chạy công cụ xử lý.'}
  if(mode==='input')return {title:'Thêm nội dung đầu vào',hint:'Tải file hoặc nhập liên kết nguồn.'}
  return {title:'Thiết lập công cụ',hint:'Mở thiết lập để hoàn thành node.'}
}

export function hasMeaningfulInput(tool:PaletteTool|undefined,params:Record<string,unknown>){
  if(!tool)return false
  return Object.entries(params).some(([name,value])=>{
    if(['model','aspect_ratio','resolution','duration','count','fanout'].includes(name))return false
    return Array.isArray(value)?value.length>0:value!==''&&value!==undefined&&value!==null&&value!==false
  })
}
