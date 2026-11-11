require 'tempfile'
require 'open3'

class PdfsController < ApplicationController
  def concatenate
    files = params[:files]

    if files.blank? || !files.is_a?(Array)
      return render json: { error: "Invalid input or missing files." }, status: :bad_request
    end

    begin
      # Create a temporary directory to hold input and output files
      Dir.mktmpdir do |dir|
        input_paths = []
        
        # Save uploaded files to disk for pdfunite to process
        files.each_with_index do |file, index|
          # Ensure we are dealing with the uploaded file object
          uploaded_file = file.is_a?(ActionDispatch::Http::UploadedFile) ? file : nil
          
          if uploaded_file.nil?
            return render json: { error: "Invalid file upload." }, status: :bad_request
          end

          path = File.join(dir, "input_#{index}.pdf")
          File.open(path, 'wb') { |f| f.write(uploaded_file.read) }
          input_paths << path
        end

        output_path = File.join(dir, "concatenated.pdf")
        
        # Construct the shell command: pdfunite file1.pdf file2.pdf output.pdf
        # Using Open3 for better error handling and security
        command = ["pdfunite"] + input_paths + [output_path]
        stdout, stderr, status = Open3.capture3(*command)

        if status.success?
          # Send the resulting PDF file
          send_file output_path, 
                    type: 'application/pdf', 
                    disposition: 'attachment', 
                    filename: 'concatenated.pdf'
        else
          Rails.logger.error "pdfunite error: #{stderr}"
          render json: { error: "An error occurred while processing the files." }, status: :internal_server_error
        end
      end
    rescue StandardError => e
      Rails.logger.error "Concatenation exception: #{e.message}"
      render json: { error: "An error occurred while processing the files." }, status: :internal_server_error
    end
  end
end