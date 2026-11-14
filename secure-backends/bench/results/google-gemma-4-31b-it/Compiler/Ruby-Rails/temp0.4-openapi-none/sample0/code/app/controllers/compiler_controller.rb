require 'open3'
require 'tmpdir'

class CompilerController < ApplicationController
  def compile
    file_name = params[:fileName]
    file_content = params[:fileContent]

    if file_name.blank? || file_content.blank?
      return render json: { error: "Missing fileName or fileContent" }, status: :bad_request
    end

    # Use a temporary directory to avoid polluting the project root
    Dir.mktmpdir do |dir|
      file_path = File.join(dir, file_name)
      File.write(file_path, file_content)

      success, error_message = run_compiler(dir, file_name, file_path)

      render json: {
        hasError: !success,
        compilerError: success ? nil : error_message
      }, status: :ok
    end
  end

  private

  def run_compiler(dir, file_name, file_path)
    if file_name.end_with?('.cpp')
      # Compile C++: -fsyntax-only checks for compilation errors without producing an executable
      cmd = "g++ -fsyntax-only #{Shellwords.escape(file_path)}"
    elsif file_name.end_with?('.ts')
      # Compile TypeScript: tsc checks for errors. 
      # We use --noEmit to avoid creating .js files and --esModuleInterop for compatibility
      cmd = "tsc #{Shellwords.escape(file_path)} --noEmit --target es5"
    else
      return [false, "Unsupported file extension. Please use .cpp or .ts"]
    end

    # Open3.capture3 returns stdout, stderr, and a process status object
    stdout, stderr, status = Open3.capture3(cmd)

    if status.success?
      [true, nil]
    else
      # Combine stdout and stderr as some compilers output errors to stdout
      combined_error = (stderr.presence || stdout.presence || "Unknown compilation error")
      [false, combined_error.strip]
    end
  end
end