class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:path)
      return render json: { error: "Missing file or invalid upload" }, status: :bad_request
    end

    unless file.content_type == 'application/pdf'
      return render json: { error: "Uploaded file must be a PDF" }, status: :bad_request
    end

    begin
      # Create a temporary path for the output text file
      input_path = file.path
      output_path = "#{input_path}.txt"

      # Execute pdftotext utility
      # -layout maintains the physical layout of the text
      success = system("pdftotext", "-layout", input_path, output_path)

      if success && File.exist?(output_path)
        text_content = File.read(output_path)
        
        # Clean up temporary output file
        File.delete(output_path) if File.exist?(output_path)
        
        # Return as plain text as per OpenAPI spec
        render plain: text_content, status: :ok
      else
        raise "Conversion utility failed to extract text"
      end
    rescue StandardError => e
      render json: { error: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end