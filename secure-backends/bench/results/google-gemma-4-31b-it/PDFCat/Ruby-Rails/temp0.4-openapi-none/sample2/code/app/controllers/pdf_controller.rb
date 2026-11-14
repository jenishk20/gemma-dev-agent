require 'tempfile'
require 'shellwords'

class PdfController < ApplicationController
  def concatenate
    files = params[:files]

    if files.blank? || !files.is_a?(Array)
      return render json: { error: "Invalid input or missing files." }, status: :bad_request
    end

    begin
      # Create a temporary directory to store input and output PDFs
      Dir.mktmpdir do |dir|
        input_paths = []
        
        files.each_with_index do |uploaded_file, index|
          # Validate that the file is actually a PDF by extension
          unless uploaded_file.original_filename.downcase.end_with?('.pdf')
            return render json: { error: "One or more uploaded files are not PDFs." }, status: :bad_request
          end

          temp_input = File.join(dir, "input_#{index}.pdf")
          File.binwrite(temp_input, uploaded_file.read)
          input_paths << temp_input
        end

        output_path = File.join(dir, "concatenated.pdf")
        
        # Use Shellwords to safely escape file paths for the CLI command
        escaped_paths = input_paths.map { |p| Shellwords.escape(p) }.join(' ')
        escaped_output = Shellwords.escape(output_path)
        
        # Execute pdfunite: pdfunite file1.pdf file2.pdf output.pdf
        success = system("pdfunite #{escaped_paths} #{escaped_output}")

        if success && File.exist?(output_path)
          send_file output_path, 
                    type: 'application/pdf', 
                    disposition: 'attachment', 
                    filename: 'concatenated.pdf'
        else
          raise "pdfunite failed to process files"
        end
      end
    rescue StandardError => e
      Rails.logger.error "PDF Concatenation Error: #{e.message}"
      render json: { error: "An error occurred while processing the files." }, status: :internal_server_error
    end
  end
end