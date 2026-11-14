require 'tempfile'
require 'open3'

class PdfsController < ApplicationController
  def concatenate
    files = params[:files]

    if files.blank? || !files.is_a?(Array)
      return render json: { error: "Invalid input or missing files." }, status: :bad_request
    end

    begin
      # Create a temporary directory to hold the input files and the output file
      Dir.mktmpdir do |dir|
        input_paths = []
        
        # Save uploaded files to the temp directory
        files.each_with_index do |file, index|
          # Rails uploads are ActionDispatch::Http::UploadedFile
          temp_input = File.join(dir, "input_#{index}.pdf")
          File.binwrite(temp_input, file.read)
          input_paths << temp_input
        end

        output_path = File.join(dir, "concatenated.pdf")
        
        # Construct the pdfunite command
        # pdfunite input1.pdf input2.pdf ... output.pdf
        cmd = ["pdfunite"] + input_paths + [output_path]
        
        stdout, stderr, status = Open3.capture3(*cmd)

        if status.success?
          # Send the resulting PDF file
          send_file output_path, 
                    type: 'application/pdf', 
                    disposition: 'attachment', 
                    filename: 'concatenated.pdf'
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