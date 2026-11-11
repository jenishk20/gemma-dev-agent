require 'zip'

class ZipConverterService
  def self.call(file_path)
    combined_text = ""
    
    # Open the zip file
    Zip::File.open(file_path) do |zip_file|
      # Iterate through all entries in the zip
      zip_file.each do |entry|
        # Only process files (not directories) and specifically text-like files
        # We check for common text extensions or just read everything that isn't a directory
        if entry.file?
          begin
            content = entry.get_input_stream.read
            combined_text << content
            combined_text << "\n" # Ensure separation between files
          rescue => e
            # Skip files that cannot be read as text
            next
          end
        end
      end
    end
    
    combined_text.strip
  end
end