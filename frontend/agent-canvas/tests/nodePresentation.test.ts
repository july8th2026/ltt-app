import { describe,expect,it } from 'vitest'
import { emptyMessage,fieldLabel,nodeModality,outputLabel,primaryFields } from '../src/nodePresentation'
import type { PaletteTool } from '../src/editorState'

const tool=(name:string,category:PaletteTool['category']='content'):PaletteTool=>({name,category,
  label:name,description:'',app_slug:'x',app_name:'X',requires:[],verifiable:[],
  params_schema:{prompt:{type:'text',required:true},model:{type:'model_ref'},seed:{type:'int'}},
  returns:{image_keys:'image[]'}})

describe('node-native presentation',()=>{
  it('maps tools to user modalities and meaningful Vietnamese labels',()=>{
    expect(nodeModality(tool('image.generate'))).toBe('image')
    expect(nodeModality(tool('video.upscale','transform'))).toBe('transform')
    expect(fieldLabel('aspect_ratio')).toBe('Tỷ lệ')
    expect(outputLabel('image_keys','image[]')).toBe('Bộ ảnh')
  })
  it('keeps technical-only fields out of the contextual composer',()=>{
    const fields=primaryFields(tool('image.generate'),{})
    expect(fields.map(([name])=>name)).toEqual(['prompt','model'])
    expect(emptyMessage(tool('image.generate')).title).toBe('Thêm một hình ảnh')
  })
})
