require 'open3'
require 'tmpdir'

class CompilerController < ApplicationController
  def compile
    file_name = params[:fileName]
    file_content = params[:fileContent]

    if file_name.blank? || file_content.blank?
      return render json: { error: "Missing fileName or fileContent" }, status: :bad_request
    end

    # Determine language by extension
    extension = File.extname(file_name).downcase
    
    # Create a temporary directory to avoid filename collisions and clutter
    Dir.mktmpdir do |dir|
      file_path = File.join(dir, file_name)
      File.write(file_path, file_content)

      case extension
      when '.cpp'
        # Compile C++: -Wall for warnings, -o for output binary
        # We only care about the compilation phase (not execution)
        cmd = "g++ -Wall \"#{file_path}\" -o \"#{dir}/a.out\""
      when '.ts'
        # Compile TypeScript: tsc checks the file. 
        # --noEmit prevents generating .js files, just checks types.
        cmd = "tsc \"#{file_path}\" --noEmit"
      else
        return render json: { error: "Unsupported file extension. Use .cpp or .ts" }, status: :bad_request
      end

      # Execute the command and capture stdout and stderr
      stdout, stderr, status = Open3.capture3(cmd)

      if status.success?
        render json: {
          hasError: false,
          compilerError: nil
        }
      else
        # For g++ and tsc, errors are usually sent to stderr
        error_message = stderr.strip.empty? ? stdout.strip : stderr.strip
        render json: {
          hasError: true,
          compilerError: error_message
        }
      end
    end
  rescue StandardError => e
    render json: { hasError: true, compilerError: e.message }, status: :internal_server_error
  end
end