import { describe,expect,it } from 'vitest'
import { emptyMessage,fieldLabel,nodeModality,nodeTitle,outputLabel,primaryFields } from '../src/nodePresentation'
import type { PaletteTool } from '../src/editorState'

const tool=(name:string,category:PaletteTool['category']='content'):PaletteTool=>({name,category,
  label:name,description:'',app_slug:'x',app_name:'X',requires:[],verifiable:[],
  params_schema:{prompt:{type:'text',required:true},model:{type:'model_ref'},seed:{type:'int'}},
  returns:{image_keys:'image[]'}})

describe('node-native presentation',()=>{
  it('maps tools to user modalities and meaningful Vietnamese labels',()=>{
    expect(nodeModality(tool('image.generate'))).toBe('image')
    expect(nodeModality(tool('asset.image','input'))).toBe('image')
    expect(nodeTitle(tool('asset.image','input'))).toBe('Hình ảnh')
    expect(nodeModality(tool('asset.images','input'))).toBe('batch')
    expect(nodeTitle(tool('asset.images','input'))).toBe('Bộ ảnh')
    expect(nodeModality(tool('video.upscale','transform'))).toBe('transform')
    expect(fieldLabel('aspect_ratio')).toBe('Tỷ lệ')
    expect(fieldLabel('image_key')).toBe('Ảnh đầu vào')
    expect(fieldLabel('image_keys')).toBe('Bộ ảnh đầu vào')
    expect(fieldLabel('source_text')).toBe('Văn bản tham chiếu')
    expect(fieldLabel('confirm_rights')).toBe('Tôi xác nhận có quyền sử dụng video')
    expect(outputLabel('image_keys','image[]')).toBe('Bộ ảnh')
  })
  it('keeps technical-only fields out of the contextual composer',()=>{
    const fields=primaryFields(tool('image.generate'),{})
    expect(fields.map(([name])=>name)).toEqual(['prompt','model'])
    expect(emptyMessage(tool('image.generate')).title).toBe('Thêm một hình ảnh')
    expect(emptyMessage(tool('video.social_import','input'))).toEqual({title:'Thêm Social Video',
      hint:'Dán liên kết TikTok, YouTube Shorts hoặc Reels mà bạn có quyền sử dụng.'})
    const asset={...tool('asset.image','input'),params_schema:{image_key:{type:'string',required:true}}}
    expect(primaryFields(asset,{})).toEqual([])
  })
})
