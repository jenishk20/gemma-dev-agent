require 'tempfile'
require 'open3'

class PdfConcatenationController < ApplicationController
  def concatenate
    files = params[:files]

    if files.blank? || !files.is_a?(Array)
      return render json: { error: "Invalid input or missing files." }, status: :bad_request
    end

    begin
      # Create a temporary directory to hold the input and output files
      Dir.mktmpdir do |dir|
        input_paths = []
        
        # Save uploaded files to the temp directory
        files.each_with_index do |file, index|
          # Rails uploads are ActionDispatch::Http::UploadedFile
          temp_pdf = File.join(dir, "input_#{index}.pdf")
          File.binwrite(temp_pdf, file.read)
          input_paths << temp_pdf
        end

        output_path = File.join(dir, "concatenated.pdf")
        
        # Construct the pdfunite command
        # pdfunite [input files] [output file]
        command = "pdfunite #{input_paths.join(' ')} #{output_path}"
        
        stdout, stderr, status = Open3.capture3(command)

        if status.success?
          # Send the resulting PDF file
          send_file output_path, type: 'application/pdf', disposition: 'attachment'
        else
          Rails.logger.error("pdfunite error: #{stderr}")
          render json: { error: "An error occurred while processing the files." }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      Rails.logger.error("Concatenation exception: #{e.message}")
      render json: { error: "An error occurred while processing the files." }, status: :internal_server_error
    end
  end
end