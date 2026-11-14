require 'open3'
require 'tempfile'

class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:tempfile)
      return render plain: "Missing file", status: :bad_request
    end

    unless file.content_type == 'application/pdf'
      return render plain: "Invalid file type. Please upload a PDF.", status: :bad_request
    end

    begin
      # We use the path of the uploaded tempfile
      input_path = file.tempfile.path
      
      # pdftotext -s (stdout) extracts text and prints it to standard output
      # We use Open3 to capture stdout and stderr separately
      stdout, stderr, status = Open3.capture3("pdftotext", "-", stdout) 
      # Note: pdftotext can read from stdin if '-' is passed, but it's safer to pass the path
      stdout, stderr, status = Open3.capture3("pdftotext", input_path, "-")

      if status.success?
        render plain: stdout, content_type: 'text/plain'
      else
        logger.error "pdftotext error: #{stderr}"
        render plain: "Conversion failed", status: :internal_server_error
      end
    rescue StandardError => e
      logger.error "Unexpected error: #{e.message}"
      render plain: "Internal Server Error", status: :internal_server_error
    end
  end
end