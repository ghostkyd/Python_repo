import win32com.client

project_path = "/path/to/your/project.kproj"
export_dir = "/path/to/export/directory"

# 连接 Kanzi Studio COM 对象（假设存在）
kanzi_app = win32com.client.Dispatch("Kanzi.Application")
project = kanzi_app.OpenProject(project_path)

# 导出为 .kzb
export_options = kanzi_app.ExportOptions()
export_options.Format = "kzb"
export_options.OutputPath = export_dir

project.Export(export_options)
project.Close()