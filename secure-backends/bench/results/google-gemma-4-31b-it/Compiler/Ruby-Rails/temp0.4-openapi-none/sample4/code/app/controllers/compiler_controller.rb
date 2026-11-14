require 'open3'
require 'tmpdir'

class CompilerController < ApplicationController
  def compile
    file_name = params[:fileName]
    file_content = params[:fileContent]

    if file_name.blank? || file_content.blank?
      return render json: { error: "Missing fileName or fileContent" }, status: :bad_request
    end

    # Security: Basic filename sanitization to prevent path traversal
    safe_name = File.basename(file_name)
    
    Dir.mktmpdir do |dir|
      file_path = File.join(dir, safe_name)
      File.write(file_path, file_content)

      if safe_name.end_with?('.cpp')
        result = compile_cpp(dir, safe_name)
      elsif safe_name.end_with?('.ts')
        result = compile_ts(dir, safe_name)
      else
        return render json: { hasError: true, compilerError: "Unsupported file extension. Please use .cpp or .ts" }
      end

      render json: result
    end
  end

  private

  def compile_cpp(dir, file_name)
    # g++ -fsyntax-only checks for compilation errors without producing an executable
    cmd = "g++ -fsyntax-only #{File.join(dir, file_name)}"
    stdout, stderr, status = Open3.capture3(cmd)

    if status.success?
      { hasError: false, compilerError: nil }
    else
      { hasError: true, compilerError: stderr.presence || stdout }
    end
  end

  def compile_ts(dir, file_name)
    # tsc checks for type errors. We use --noEmit to avoid generating .js files
    cmd = "tsc #{File.join(dir, file_name)} --noEmit --esModuleInterop"
    stdout, stderr, status = Open3.capture3(cmd)

    if status.success?
      { hasError: false, compilerError: nil }
    else
      # tsc usually outputs errors to stdout
      error_msg = stdout.presence || stderr
      { hasError: true, compilerError: error_msg }
    end
  end
end