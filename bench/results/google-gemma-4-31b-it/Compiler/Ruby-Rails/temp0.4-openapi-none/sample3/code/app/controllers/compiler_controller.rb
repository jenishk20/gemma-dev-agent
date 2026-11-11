require 'open3'
require 'tmpdir'

class CompilerController < ApplicationController
  def compile
    file_name = params[:fileName]
    file_content = params[:fileContent]

    if file_name.blank? || file_content.blank?
      return render json: { error: "Missing fileName or fileContent" }, status: :bad_request
    end

    # Use a temporary directory to avoid filename collisions and security issues
    Dir.mktmpdir do |dir|
      file_path = File.join(dir, file_name)
      File.write(file_path, file_content)

      if file_name.end_with?('.ts')
        result = compile_typescript(dir, file_name)
      elsif file_name.end_with?('.cpp')
        result = compile_cpp(dir, file_name)
      else
        return render json: { hasError: true, compilerError: "Unsupported file extension. Please use .ts or .cpp" }
      end

      if result[:success]
        render json: { hasError: false, compilerError: nil }
      else
        render json: { hasError: true, compilerError: result[:error] }
      end
    end
  rescue StandardError => e
    render json: { hasError: true, compilerError: "Internal Server Error: #{e.message}" }, status: :internal_server_error
  end

  private

  def compile_typescript(dir, file_name)
    # Run tsc (TypeScript Compiler)
    # We change directory to the tmp dir so the compiler output references the filename correctly
    stdout, stderr, status = Open3.capture3("tsc #{file_name}", chdir: dir)
    
    # tsc outputs errors to stdout
    if status.success?
      { success: true }
    else
      # Combine stdout and stderr for the full compiler feedback
      error_msg = (stdout + stderr).strip
      { success: false, error: error_msg.presence || "TypeScript compilation failed" }
    end
  end

  def compile_cpp(dir, file_name)
    # Run g++
    stdout, stderr, status = Open3.capture3("g++ #{file_name} -o a.out", chdir: dir)
    
    if status.success?
      { success: true }
    else
      # g++ outputs errors to stderr
      error_msg = (stderr + stdout).strip
      { success: false, error: error_msg.presence || "C++ compilation failed" }
    end
  end
end