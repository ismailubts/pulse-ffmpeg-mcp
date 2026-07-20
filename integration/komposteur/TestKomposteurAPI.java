import no.lau.komposteur.core.KomposteurEntryPoint;

public class TestKomposteurAPI {
    public static void main(String[] args) {
        try {
            System.out.println("Testing Komposteur API...");
            
            KomposteurEntryPoint komposteur = new KomposteurEntryPoint();
            komposteur.initialize();
            
            System.out.println("✅ Komposteur initialized successfully");
            
            // Test status
            System.out.println("Status: " + komposteur.getStatus());
            
            // Test with the kompost.json file if it exists
            if (args.length > 0) {
                System.out.println("Processing: " + args[0]);
                String result = komposteur.processKompost(args[0]);
                System.out.println("✅ Processing result: " + result);
            } else {
                System.out.println("⚠️  No kompost.json file provided as argument");
            }
            
            komposteur.shutdown();
            System.out.println("✅ Komposteur shutdown successfully");
            
        } catch (Exception e) {
            System.err.println("❌ Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}