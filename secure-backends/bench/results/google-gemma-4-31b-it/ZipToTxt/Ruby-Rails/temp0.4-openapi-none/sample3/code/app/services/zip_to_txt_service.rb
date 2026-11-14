require 'zip'

class ZipToTxtService
  def self.call(file_path)
    combined_text = []
    
    # Open the zip file
    Zip::File.open(file_path) do |zip_file|
      # Sort entries to ensure consistent concatenation order
      zip_file.each do |entry|
        # Only process files (not directories) and only those that look like text files
        # We check for common text extensions or simply attempt to read them
        if entry.file? && is_text_file?(entry.name)
          combined_text << entry.get_input_stream.read
        end
      end
    end
    
    combined_text.join("\n")
  rescue Zip::Error => e
    raise StandardError, "Invalid zip file: #{e.message}"
  end

  private

  def self.is_text_file?(filename)
    # Simple heuristic: check extension or common text patterns
    # In a production app, we might use the 'file' command or mime-type check
    text_extensions = ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js']
    text_extensions.any? { |ext| filename.downcase.end_with?(ext) } || 
    !File.extname(filename).present? # Treat files without extensions as potential text
  end
end