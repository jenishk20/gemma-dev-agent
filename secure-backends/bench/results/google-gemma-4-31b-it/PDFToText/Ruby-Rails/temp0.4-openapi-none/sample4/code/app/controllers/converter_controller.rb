require 'open3'

class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil?
      return render json: { error: 'Missing file parameter' }, status: :bad_request
    end

    unless file.content_type == 'application/pdf'
      return render json: { error: 'Invalid file type. Please upload a PDF.' }, status: :bad_request
    end

    begin
      # Save the uploaded file to a temporary location
      temp_pdf = file.tempfile.path
      
      # pdftotext - reads from PDF and outputs to stdout by default if no output file is specified
      # We use Open3 to capture the stdout of the command
      stdout, stderr, status = Open3.capture3("pdftotext", temp_pdf)

      if status.success?
        # Return as plain text as per OpenAPI spec
        render plain: stdout, content_type: 'text/plain'
      else
        logger.error "pdftotext error: #{stderr}"
        render json: { error: 'Conversion failed' }, status: :internal_server_error
      end
    rescue StandardError => e
      logger.error "Unexpected error: #{e.message}"
      render json: { error: 'Internal Server Error' }, status: :internal_server_error
    end
  end
end