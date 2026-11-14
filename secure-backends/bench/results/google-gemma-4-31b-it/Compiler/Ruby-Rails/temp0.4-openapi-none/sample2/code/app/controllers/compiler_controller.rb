require 'open3'
require 'tempfile'

class CompilerController < ApplicationController
  def compile
    file_name = params[:fileName]
    file_content = params[:fileContent]

    if file_name.blank? || file_content.blank?
      return render json: { error: "Missing fileName or fileContent" }, status: :bad_request
    end

    # Create a temporary directory to isolate the file
    Dir.mktmpdir do |dir|
      file_path = File.join(dir, file_name)
      File.write(file_path, file_content)

      if file_name.end_with?('.ts')
        result = compile_typescript(file_path)
      elsif file_name.end_with?('.cpp')
        result = compile_cpp(file_path)
      else
        return render json: { error: "Unsupported file extension. Use .ts or .cpp" }, status: :unprocessable_entity
      end

      if result[:success]
        render json: { hasError: false, compilerError: nil }, status: :ok
      else
        render json: { hasError: true, compilerError: result[:error] }, status: :ok
      end
    end
  end

  private

  def compile_typescript(path)
    # tsc command for compilation check
    # --noEmit prevents generating .js files
    stdout, stderr, status = Open3.capture3("tsc #{path} --noEmit")
    
    # tsc outputs errors to stdout
    if status.success?
      { success: true }
    else
      { success: false, error: (stdout + stderr).strip }
    end
  end

  def compile_cpp(path)
    # g++ command for compilation check
    # -fsyntax-only checks for compilation errors without producing an executable
    stdout, stderr, status = Open3.capture3("g++ -fsyntax-only #{path}")
    
    if status.success?
      { success: true }
    else
      { success: false, error: (stdout + stderr).strip }
    end
  end
end